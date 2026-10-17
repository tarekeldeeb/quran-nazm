"""Joint page and line breaking for a hizb, solved exactly.

For a common line width W (font units) the layout of a hizb is the solution of

    minimise    sum over all text lines l of (log(W / n_l))^2          (n_l: natural width)
    subject to  exactly 10 pages, page breaks at ayah ends, line breaks at word ends,
                every surah starts on a new line under its header,
                no surah title below TITLE_MAX_ROW,
                n_l <= W / (1 - shrink)  (no line compressed beyond the limit),

plus a fixed penalty for breaking a page inside a surah short enough for one page.
Widths are the HarfBuzz-shaped advances of each word in the DigitalKhatt font (an
ayah marker glued to its word) plus the font's word space, never word or letter
counts.

The problem is a chain: a page's cost depends only on its own ayahs, and a line's
only on its own words. It is therefore solved exactly by nested dynamic programming:

  1. for each surah segment of a candidate page and each line count n, the best
     cut of its words into n lines;
  2. for the candidate page, the best share of its 15 - headers lines among its
     segments (an exact allocation, with the title-row constraint);
  3. for the hizb, the best 10 pages (a shortest path with exactly 10 arcs).

The common width W couples the hizbs; `min_width` bisects on it for the smallest W
(largest type) at which every hizb is feasible. `milp_pages` restates step 3 as an
integer program for HiGHS, to check the dynamic programme's optimum.
"""
import math

import numpy as np
from numba import njit

import render_mushaf as R

INF = 1e30
SPLIT_PENALTY = 5.0  # a page break inside a surah that fits on one page (a typical page costs ~0.03)
WINDOW = 40          # at most this many words on a line


@njit(cache=True)
def _segment_costs(cum, a, b, L, W, Wmax, sp):
    """g[n] = least cost of cutting words a..b-1 into n lines (n = 1..L)."""
    m = b - a
    best = np.full((L + 1, m + 1), INF)
    best[0, 0] = 0.0
    for k in range(1, L + 1):
        for e in range(k, m + 1):
            lo = max(k - 1, e - WINDOW)
            for s in range(lo, e):
                prev = best[k - 1, s]
                if prev >= INF:
                    continue
                nat = cum[a + e] - cum[a + s] - sp
                if nat > Wmax:
                    continue  # s only grows the line further left; earlier s are wider still
                r = math.log(W / nat)
                c = prev + r * r
                if c < best[k, e]:
                    best[k, e] = c
    g = np.full(L + 1, INF)
    for n in range(1, L + 1):
        g[n] = best[n, m]
    return g


@njit(cache=True)
def _page_cost(cum, seg_a, seg_b, seg_h, W, Wmax, sp, lines, title_max):
    """Least cost of one page: segments seg_a[t]..seg_b[t] (word indices), header
    lines seg_h[t]; returns (cost, allocation)."""
    S = len(seg_a)
    H = 0
    for t in range(S):
        H += seg_h[t]
    L = lines - H
    alloc = np.zeros(S, np.int64)
    if L < S:
        return INF, alloc
    G = np.full((S, L + 1), INF)
    for t in range(S):
        G[t] = _segment_costs(cum, seg_a[t], seg_b[t], L, W, Wmax, sp)
    # A[t, u]: best cost of segments 0..t-1 using u text lines
    A = np.full((S + 1, L + 1), INF)
    back = np.zeros((S + 1, L + 1), np.int64)
    A[0, 0] = 0.0
    hsum = 0
    for t in range(S):
        for u in range(L + 1):
            if A[t, u] >= INF:
                continue
            if seg_h[t] > 0 and 1 + hsum + u > title_max:
                continue  # this segment's title would fall below title_max
            for n in range(1, L - u + 1):
                c = A[t, u] + G[t, n]
                if c < A[t + 1, u + n]:
                    A[t + 1, u + n] = c
                    back[t + 1, u + n] = n
        hsum += seg_h[t]
    cost = A[S, L]
    if cost < INF:
        u = L
        for t in range(S, 0, -1):
            alloc[t - 1] = back[t, u]
            u -= back[t, u]
    return cost, alloc


class Hizb:
    """Word widths and structure of a run of ayahs."""

    def __init__(self, txt, ayahs):
        self.txt, self.ayahs = txt, ayahs
        self.units = [txt.units(s, a) for s, a in ayahs]
        w = [x for u in self.units for _, x in u]
        self.cum = np.concatenate([[0.0], np.cumsum(np.array(w) + txt.sp)])
        self.aw = np.concatenate([[0], np.cumsum([len(u) for u in self.units])]).astype(np.int64)
        self.head = np.array([R.header_lines(s) if a == 1 else 0 for s, a in ayahs], np.int64)
        n = len(ayahs)
        span = {}
        for i, (s, a) in enumerate(ayahs):
            span.setdefault(s, [i, i])[1] = i
        self.short = np.zeros(n + 1, bool)  # a break at i would split a surah that fits on one page
        self.span = span
        assert len(self.cum) == self.aw[-1] + 1

    def segments(self, j, i):
        seg_a, seg_b, seg_h = [], [], []
        for k in range(j, i):
            if k == j or self.ayahs[k][1] == 1:
                seg_a.append(self.aw[k])
                seg_b.append(self.aw[k])
                seg_h.append(self.head[k])
            seg_b[-1] = self.aw[k + 1]
        return np.array(seg_a, np.int64), np.array(seg_b, np.int64), np.array(seg_h, np.int64)

    def page(self, j, i, W, Wmax):
        a, b, h = self.segments(j, i)
        return _page_cost(self.cum, a, b, h, W, Wmax, self.txt.sp, R.LINES, R.TITLE_MAX_ROW)

    def mark_short(self, W):
        """Breaks inside a whole surah that would fit on one page at width W."""
        self.short[:] = False
        for s, (i0, i1) in self.span.items():
            whole = self.ayahs[i0][1] == 1 and self.ayahs[i1][1] == len(self.txt.suras[s - 1]["ayas"])
            if not whole:
                continue
            words = self.cum[self.aw[i1 + 1]] - self.cum[self.aw[i0]]
            if R.header_lines(s) + math.ceil(words / W) <= R.LINES:
                self.short[i0 + 1:i1 + 1] = True

    def page_table(self, W, shrink):
        """cost[(j, i)] for every page that fits within the shrink limit."""
        Wmax = W / (1 - shrink)
        self.mark_short(W)
        cost = {}
        n = len(self.ayahs)
        for j in range(n):
            for i in range(j + 1, n + 1):
                words = self.cum[self.aw[i]] - self.cum[self.aw[j]]
                if words > Wmax * R.LINES:
                    break
                c, _ = self.page(j, i, W, Wmax)
                if c < INF:
                    cost[j, i] = c + (SPLIT_PENALTY if i < n and self.short[i] else 0.0)
        return cost


def best_pages(hz, W, shrink, pages=R.PAGES_PER_HIZB, cost=None):
    """Exact 10-page cut (shortest path with exactly `pages` arcs). None if infeasible."""
    cost = hz.page_table(W, shrink) if cost is None else cost
    n = len(hz.ayahs)
    out = {}
    for (j, i), c in cost.items():
        out.setdefault(i, []).append((j, c))
    best = np.full((pages + 1, n + 1), INF)
    back = np.zeros((pages + 1, n + 1), int)
    best[0, 0] = 0
    for k in range(1, pages + 1):
        for i in range(1, n + 1):
            for j, c in out.get(i, ()):
                v = best[k - 1, j] + c
                if v < best[k, i]:
                    best[k, i], back[k, i] = v, j
    if best[pages, n] >= INF:
        return None, INF
    cuts, k = [n], pages
    while k:
        cuts.append(back[k, cuts[-1]])
        k -= 1
    cuts = cuts[::-1]
    return list(zip(cuts[:-1], cuts[1:])), float(best[pages, n])


def milp_pages(hz, cost, pages=R.PAGES_PER_HIZB):
    """The same page problem as an integer programme (flow with exactly `pages`
    arcs), solved by HiGHS; returns its optimal value."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    arcs = list(cost)
    n = len(hz.ayahs)
    A = lil_matrix((n + 2, len(arcs)))
    for k, (j, i) in enumerate(arcs):
        A[j, k] -= 1  # leaves node j
        A[i, k] += 1  # enters node i
        A[n + 1, k] = 1
    rhs = np.zeros(n + 2)
    rhs[0], rhs[n], rhs[n + 1] = -1, 1, pages
    res = milp(c=np.array([cost[a] for a in arcs]), integrality=np.ones(len(arcs)),
               bounds=Bounds(0, 1), constraints=LinearConstraint(A.tocsr(), rhs, rhs))
    return res.fun


def rows_for(hz, j, i, W, Wmax):
    """Rows of a page in render_mushaf's format, from the exact allocation."""
    a, b, h = hz.segments(j, i)
    _, alloc = hz.page(j, i, W, Wmax)
    words = [t for u in hz.units[j:i] for t, _ in u]
    w = [x for u in hz.units[j:i] for _, x in u]
    base = hz.aw[j]
    rows = []
    for t in range(len(a)):
        s = None
        for kk in range(j, i):  # surah of this segment
            if hz.aw[kk] == a[t]:
                s = hz.ayahs[kk][0]
                break
        if h[t]:
            rows.append(("title", s))
            if h[t] == 2:
                rows.append(("basmala",))
        ws = w[a[t] - base:b[t] - base]
        tx = words[a[t] - base:b[t] - base]
        for x, y in _cuts(hz, a[t], b[t], int(alloc[t]), W, Wmax):
            nat = sum(ws[x:y]) + hz.txt.sp * (y - x - 1)
            rows.append(("text", tx[x:y], nat))
    return rows


def _cuts(hz, a, b, n, W, Wmax):
    """Word cuts of one segment into n lines (same DP as _segment_costs, with back pointers)."""
    m, sp, cum = b - a, hz.txt.sp, hz.cum
    best = np.full((n + 1, m + 1), INF)
    back = np.zeros((n + 1, m + 1), int)
    best[0, 0] = 0
    for k in range(1, n + 1):
        for e in range(k, m + 1):
            for s in range(max(k - 1, e - WINDOW), e):
                if best[k - 1, s] >= INF:
                    continue
                nat = cum[a + e] - cum[a + s] - sp
                if nat > Wmax:
                    continue
                c = best[k - 1, s] + math.log(W / nat) ** 2
                if c < best[k, e]:
                    best[k, e], back[k, e] = c, s
    cuts, k = [m], n
    while k:
        cuts.append(back[k, cuts[-1]])
        k -= 1
    cuts = cuts[::-1]
    return list(zip(cuts[:-1], cuts[1:]))

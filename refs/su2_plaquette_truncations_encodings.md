# Truncations and Encodings for the SU(2) Plaquette with Outer Links

*Dr. Md Habib E Islam (Digonto) · 4 November 2026*

With open outer links, this diagram has **433** gauge-invariant spin-network states at $j_{\max}=1/2$ and **65,250** at $j_{\max}=1$. The $n$-qubit link-label encoding ($n=12$ here) captures only 256 of the 433, because some corners hold two singlets. Every number below comes from `su2_plaquette_encodings.py`.

---

## 1. The diagram

The test system is one square plaquette with 4 inner links and 8 outer links: $L = 12$ links and $V = 4$ vertices. Every vertex is 4-valent (4 links meet there), as in the bulk of a 2D square lattice.

- **Link variable** $U_\mu(x)$: the $2\times 2$ SU(2) matrix on the link that starts at site $x$ and points in direction $\hat\mu$ ($\hat 1$ = right, $\hat 2$ = up).
- **Inner links** (the loop): $U_1(0,0)$, $U_2(1,0)$, $U_1(0,1)$, $U_2(0,0)$.
- **Outer links** (two per corner): $U_1(-1,0)$, $U_2(0,-1)$, $U_1(1,0)$, $U_2(1,-1)$, $U_1(-1,1)$, $U_2(0,1)$, $U_1(1,1)$, $U_2(1,1)$.
- **Plaquette operator**: the product of links around the loop. It changes only the 4 inner links.

$$
U_P = U_1(0,0)\,U_2(1,0)\,U_1(0,1)^\dagger\,U_2(0,0)^\dagger
$$

- **Gauss's law**: at each corner, the 4 links meeting there must combine into an SU(2) singlet (zero net colour charge). States that obey it at every corner are called *physical* or *gauge-invariant*.
- **Far ends of the outer links** touch nothing. You must choose how to treat them. This file counts states for the *open* choice (far ends free) and the *closed* choice (outer links fixed to $j=0$, which reduces to an isolated plaquette).

---

## 2. Why truncate

Each SU(2) link has an infinite-dimensional Hilbert space, so it must be cut to a finite size before it fits on qubits. *Truncation* is the rule for that cut. Different rules keep different symmetries, which is why several schemes exist.

- **Electric (irrep) basis**: the standard basis of the Kogut–Susskind Hamiltonian. A link state is $|j, m_L, m_R\rangle$: the spin $j$ (an SU(2) irreducible representation, or *irrep*) and one magnetic number for each end of the link.
- **Electric energy** is diagonal in this basis and grows with $j$:

$$
H_E = \frac{g^2}{2}\sum_{\text{links}} j(j+1)
$$

- **One link** at spin $j$ holds $(2j+1)^2$ states. Summed up to a cutoff $j_{\max}$:

$$
d_{\text{link}}(j_{\max}) = \sum_{j=0}^{j_{\max}} (2j+1)^2
$$

- This gives **5 states per link** at $j_{\max}=1/2$ and **14** at $j_{\max}=1$.
- **Why $j_{\max}$ works at strong coupling**: large $j$ costs electric energy, so high-$j$ states are rare when $g$ is large. Toward the continuum (small $g$), $j_{\max}$ must grow and other schemes become competitive.

---

## 3. Truncation schemes

The schemes differ in *what* they cut. $j_{\max}$ and q-deformation cut the spin label; the group-element methods cut the set of matrices; orbifold and fuzzy replace the link variable with something finite by construction.

| Scheme | What is cut | What survives exactly | Size per link | Source |
| --- | --- | --- | --- | --- |
| **$j_{\max}$ (irrep truncation)** | keep spins $j \le j_{\max}$ in the electric basis | SU(2) Gauss's law at every vertex | $\sum_j (2j+1)^2$: 5 at $j_{\max}=1/2$, 14 at $j_{\max}=1$ | Kogut–Susskind; standard |
| **q-deformed, SU(2)$_k$** | spins $j \le k/2$; coupling rule gains $j_1+j_2+j_3 \le k$ | quantum-group gauge invariance; spin-network F-moves stay unitary | $k+1$ spin labels | [Zache, González-Cuadra, Zoller](https://arxiv.org/pdf/2304.02527) |
| **Discrete subgroup (group-element basis)** | replace SU(2) by a finite subgroup $G$ | exact $G$ gauge invariance, not SU(2) | $\lceil\log_2\lvert G\rvert\rceil$: 5 for $2T$ (24), 6 for $2O$ (48), 7 for $2I$ (120) | [Lamm, Lawrence, Yamauchi](https://arxiv.org/abs/1903.08807) |
| **Orbifold lattice** | $U$ becomes a non-compact complex matrix $Z$; each real component is a boson on $2^Q$ grid points | SU(2) recovered only as a mass term $\to\infty$ | $4Q$ qubits (minimal SU(2) embedding) or $8Q$ | [Halimeh et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12916482), [Bergner, Hanada, Mendicelli](https://arxiv.org/pdf/2604.15132) |
| **Fuzzy gauge theory** | each matrix element of $U$ becomes a $D\times D$ matrix | the usual gauge symmetry, by construction | $D^2$ states; $D=4$ gives 16 (4 qubits) | [Alexandru, Bedaque et al.](https://arxiv.org/html/2308.05253v4) |
| **Quantum link model (rishons)** | $U$ built from fermion pairs at the two ends, fixed fermion number | exact gauge invariance of a related U(2)-type theory | 6 states in the minimal SU(4)-embedding sector | [Brower, Chandrasekharan, Wiese](https://arxiv.org/pdf/hep-th/9704106v1) |

- **Orbifold**: the large-mass limit recovers Kogut–Susskind. The truncation is in boson grid points, not in spin $j$.
- **Fuzzy**: the paper offers two kinetic terms, $\mathcal K_1$ (Casimir-like) and $\mathcal K_2$ (built from $\mathcal U$). Its single-plaquette circuit uses 16 qubits.

### Binary register (how a label is stored)

A *register* is the group of qubits holding one label. The same label can be stored several ways, which changes the qubit count and the gates.

- **Binary**: $d$ values in $\lceil\log_2 d\rceil$ qubits. Fewest qubits; unused bit-strings (when $d$ is not a power of 2) are *leakage* states that a circuit must avoid.
- **Unary / one-hot**: $d$ values in $d$ qubits, exactly one set to 1. More qubits, but simpler controlled gates and a cheap error check.
- **Gray code**: binary order chosen so neighbouring values differ by one bit, which makes $j \to j \pm 1/2$ steps cheaper.
- **Qudit**: a native $d$-level system on hardware that has one.

---

## 4. Encodings

An *encoding* maps the truncated states onto qubits. The main split is whether Gauss's law is built in (only physical states can be written) or checked afterwards (the register also holds unphysical states).

### 4.1 $n$-qubit encoding (one spin label per link)

- Store one spin label $j \in \{0, \tfrac12, \dots, j_{\max}\}$ on every link. The qubit count $n$ is set by the number of links $L$, not fixed in advance:

$$
n = L\,b, \qquad b = \lceil \log_2(2j_{\max}+1) \rceil, \qquad L = L_{\text{inner}} + L_{\text{outer}}
$$

- **This diagram**: $L = 4 + 8 = 12$, so $n = 12$ at $j_{\max}=1/2$ and $n = 24$ at $j_{\max}=1$. A closed plaquette ($L=4$) gives $n=4$ and $8$. More outer links, or a bigger lattice, grow $n$ the same way.
- **The catch at 4-valent corners**: when all four links at a corner carry $j=1/2$, there are two singlets (intermediate spin $J=0$ or $1$). Link labels alone cannot tell them apart.
- **Fix**: add one intertwiner register per corner,

$$
n = L\,b + V\,c ,
$$

  with $V=4$ corners and $c$ qubits per intertwiner. Point-splitting does this with 4 virtual links carrying $J \le 2j_{\max}$: $n = 12\cdot1 + 4\cdot2 = 20$ at $j_{\max}=1/2$ and $n = 12\cdot2 + 4\cdot3 = 36$ at $j_{\max}=1$.
- **When link labels alone are enough**: q-deformed SU(2)$_1$, or if $J$ is also cut at $j_{\max}$.

### 4.2 Spin network (intertwiner basis)

- Store one spin $j$ per link **plus** one *intertwiner* label per vertex. An intertwiner is the label that picks which singlet a vertex is in; at a 4-valent corner it is the intermediate spin $J$.
- Every basis state is gauge-invariant by construction. The plaquette operator acts through $6j$/$9j$ recoupling coefficients and depends on the outer links.
- **Point-splitting**: split each 4-valent corner into two 3-valent sites joined by a short *virtual link* carrying $J$. On 3-valent sites the link spins fix the state, so no separate intertwiner label is needed.

### 4.3 Rishon (quantum link model)

- Write each link as a fermion pair, one *rishon* at each end:

$$
U^{ab}_{x,\mu} = c^{a}_{x,+\mu}\, c^{b\,\dagger}_{x+\hat\mu,-\mu}
$$

- For SU(2): 2 colours $\times$ 2 ends = 4 fermion modes, so 4 qubits per link via the Jordan–Wigner map.
- Fixing 2 rishons per link leaves $\binom{4}{2}=6$ states: two singlets plus one $(\tfrac12,\tfrac12)$ quartet. Compare the 5 states of $j_{\max}=1/2$.
- Gauss's law becomes a local fermion-number-like rule; this suits cold-atom and fermionic hardware.

### 4.4 Loop-string-hadron (LSH)

- Start from *prepotentials*: Schwinger bosons at each end of each link that build SU(2) from harmonic oscillators.
- On a point-split (3-valent) lattice, the gauge-invariant data at each site is a set of non-negative integers: loop numbers between pairs of legs (and, with quarks, string and hadron numbers).
- The non-Abelian Gauss law is solved locally. What remains is an **Abelian-like** rule: the flux read from both ends of a link must agree.
- For pure gauge it spans the same space as the spin network, with local integer labels instead of recoupling coefficients. Reference: [Raychowdhury & Stryker](https://ar5iv.labs.arxiv.org/html/1912.06133).

### 4.5 Other encodings the truncations need

- **Full electric basis** $|j, m_L, m_R\rangle$ per link: the $j_{\max}$ truncation without imposing Gauss's law. Simple local gates, but most states are unphysical; Gauss's law is enforced by a penalty term or checked by measurement.
- **Group-element (magnetic) basis**: one register per link holding an element of the finite subgroup $G$. The plaquette is diagonal here; the electric term needs a group Fourier transform.
- **Boson-grid encoding (orbifold)**: each real boson on $2^Q$ grid points in binary, $Q$ qubits per boson.
- **Fuzzy link register**: $D^2$ states per link, so $\lceil\log_2 D^2\rceil$ qubits.
- **q-deformed spin network**: the spin-network register with SU(2)$_k$ labels. Its coupling rule removes some intertwiners.

---

## 5. Numbers on this diagram

### Gauge-invariant state counts

| Boundary choice | $j_{\max}=1/2$ | $j_{\max}=1$ |
| --- | --- | --- |
| Closed (outer links $j=0$) | 2 | 3 |
| Open, spin-network labels | 433 | 65,250 |
| Open, full Hilbert space (far-end index free) | 17,362 | 33,083,923 |
| q-deformed SU(2)$_k$, $k=2j_{\max}$, closed | 2 | 3 |
| q-deformed SU(2)$_k$, $k=2j_{\max}$, open labels | 256 | 18,464 |

- **Closed**: the loop carries one spin $j \in \{0,\dots,j_{\max}\}$, giving $2j_{\max}+1$ states.
- **Link labels alone** at $j_{\max}=1/2$: $2^{12} = 4096$ bit-strings, 256 obey the corner rules, and 95 of those have a corner with two singlets. That is why $433 > 256$.
- **q-deformed SU(2)$_1$** removes the $J=1$ intertwiner, so its open count is exactly 256: there the $n$-qubit link-label register is complete.

### Register sizes (qubits, all links of this diagram)

| Encoding | $j_{\max}=1/2$ | $j_{\max}=1$ | Gauss's law |
| --- | --- | --- | --- |
| $n$-qubit, one spin label per link (binary, $L=12$) | 12 | 24 | built in, but misses intertwiners |
| Spin label per link, unary | 24 | 36 | same as above |
| Spin network (labels + intertwiner per corner, point-split) | 20 | 36 | built in |
| q-deformed spin network ($k=2j_{\max}$) | 16 | 32 | built in |
| LSH, point-split (8 sites $\times$ 3 loop numbers) | 24 | 48 | non-Abelian part built in; Abelian-like link checks |
| Full electric basis $\lvert j\,m_L\,m_R\rangle$ | 36 | 48 | not built in |
| Rishon quantum link model | 48 | 48 | local fermion-number rule |
| Fuzzy, $D=4$ | 48 | 48 | built into the algebra |
| Group element, $2T$ / $2O$ / $2I$ | 60 / 72 / 84 | 60 / 72 / 84 | not built in (exact for $G$ only) |
| Orbifold, 4 bosons/link, $Q=3$ | 144 | 144 | recovered as mass $\to\infty$ |

- At $j_{\max}=1/2$ one intertwiner qubit per corner is enough ($n=16$), and in q-deformed SU(2)$_1$ none is needed ($n=12$).
- Rishon, fuzzy, group-element and orbifold rows do not depend on $j_{\max}$; each has its own size knob (rishon number, $D$, $G$, $Q$).
- Every row scales with the link count $L$: changing the number of outer links changes $n$ in each row proportionally.

---

## 6. The script

`su2_plaquette_encodings.py` reproduces every number above in under a second. Run `python3 su2_plaquette_encodings.py`; it needs only numpy.

1. **Gauss-law check**: for every choice of 4 spins at a corner (16 at $j_{\max}=1/2$, 81 at $j_{\max}=1$), it builds the total spin operator $\mathbf S^2$, counts its zero eigenvalues (the singlets) and compares with the intertwiner formula. Result: 0 mismatches.
2. **State counts**: sums the product of corner intertwiner counts over all link spins, for closed and open outer links, with ordinary SU(2) or SU(2)$_k$ coupling rules.
3. **$n$-qubit test**: computes $n = L\,b$ for $L = 4$, $12$ and the point-split graph, enumerates all link-label strings, and flags corners where labels alone are ambiguous.
4. **Register sizes**: binary and unary qubit counts for each encoding in the table.

It does **not** yet build Hamiltonians or circuits. The natural next step is the plaquette operator in the spin-network basis ($6j$/$9j$ coefficients), then a gate count per encoding.

---

## 7. Assumptions and open questions

- **Outer-link far ends**: counts are given for closed and open choices. Fixing outer links to chosen spins (static boundary charges) is a third option the script can add.
- **Intertwiner cutoff**: the $j_{\max}$ counts let the intermediate spin $J$ reach $2j_{\max}$ ($J=1$ at $j_{\max}=1/2$). Truncating $J$ too would drop the open count to 256.
- **Rishon count of 6 states** and its split (two singlets + one $(\tfrac12,\tfrac12)$ quartet) are derived here from fermion counting, not quoted from a paper.
- **Subgroup orders** (24, 48, 120) are standard group theory; not stated in the cited paper.
- **Orbifold qubits per link** ($4Q$) is inferred from 4 bosons per link and $Q$ qubits per boson; the paper gives no per-link total.
- **Fuzzy details** (16-qubit plaquette circuit, which kinetic term is used) came from a summary of the paper and should be checked against the text.
- **$n$ grows with the link count**: the "12-qubit" name was a placeholder; the encoding is $n$-qubit, with $n$ set by the links in the diagram ($n=12$ only for 12 links at $j_{\max}=1/2$).

## Sources

- [Zache, González-Cuadra, Zoller — q-deformed spin networks (arXiv:2304.02527)](https://arxiv.org/pdf/2304.02527)
- [Alexandru, Bedaque et al. — Fuzzy gauge theory for quantum computers (arXiv:2308.05253)](https://arxiv.org/html/2308.05253v4)
- [Halimeh et al. — A universal framework for the quantum simulation of Yang–Mills theory](https://pmc.ncbi.nlm.nih.gov/articles/PMC12916482)
- [Bergner, Hanada, Mendicelli — A minimal implementation of Yang–Mills theory (arXiv:2604.15132)](https://arxiv.org/pdf/2604.15132)
- [Brower, Chandrasekharan, Wiese — QCD as a quantum link model (hep-th/9704106)](https://arxiv.org/pdf/hep-th/9704106v1)
- [Wiese — Quantum simulation of lattice gauge theories (arXiv:1305.1602)](https://arxiv.org/pdf/1305.1602v1)
- [Lamm, Lawrence, Yamauchi — General methods for digital quantum simulation of gauge theories (arXiv:1903.08807)](https://arxiv.org/abs/1903.08807)
- [Raychowdhury & Stryker — Loop, string and hadron dynamics in SU(2) (arXiv:1912.06133)](https://ar5iv.labs.arxiv.org/html/1912.06133)

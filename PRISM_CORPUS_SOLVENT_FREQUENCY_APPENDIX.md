# Prism Corpus Solvent Frequency Appendix

## Scope

This appendix reports the actual solvent-frequency distribution for the current canonical processed corpus after enabling water-solubility supervision.

Methodology:

- Source files: `notebooks/data/processed/train.csv`, `val.csv`, `test.csv`.
- The frequency table below uses the solubility-supervised subset only, i.e. rows with `has_solubility=True`.
- Solvent identity is reported as `solvent_name` when present, otherwise `solvent_smiles`.
- Because the solvent is fixed within each row group, `n_unique_solutes` is also the number of unique `(solute, solvent)` pairs for that solvent.

## Executive Summary

- Solubility-supervised rows: `108,287`.
- Unique solvents in the supervised subset: `213`.
- Top 5 solvents account for `37.05%` of all supervised rows.
- Top 10 solvents account for `62.10%`.
- Top 20 solvents account for `79.07%`.
- Concentration metrics: `HHI = 0.0457`, `Gini = 0.8696`.
- The dominant solvents are now `ethanol`, `methanol`, `isopropanol`, `ethyl acetate`, and `n-propanol`; `water` is now rank `6` in the supervised subset.
- `water` contributes `6,524` supervised rows and `18,397` auxiliary-only rows in the current canonical processed CSVs.
- `acetone` is rank `7` with `6,263` rows (5.78%).
- `DMSO` is rank `23` with `1,106` rows (1.02%).

## Top 20 Solvents

| Rank | Solvent | SMILES | Records | Share (%) | Unique solutes/pairs | T min (K) | T median (K) | T max (K) | Median ln x2 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | ethanol | `CCO` | 10247 | 9.46 | 1084 | 248.20 | 303.15 | 360.15 | -5.0468 |
| 2 | methanol | `CO` | 8379 | 7.74 | 907 | 248.20 | 303.15 | 354.15 | -4.8643 |
| 3 | isopropanol | `CC(C)O` | 7532 | 6.96 | 809 | 252.05 | 303.15 | 363.15 | -5.1898 |
| 4 | ethyl acetate | `CCOC(C)=O` | 7106 | 6.56 | 776 | 248.20 | 303.15 | 348.15 | -4.2944 |
| 5 | n-propanol | `CCCO` | 6855 | 6.33 | 720 | 248.20 | 303.15 | 368.15 | -4.8254 |
| 6 | water | `O` | 6524 | 6.02 | 737 | 273.15 | 305.54 | 373.15 | -7.8248 |
| 7 | acetone | `CC(C)=O` | 6263 | 5.78 | 688 | 248.20 | 303.15 | 355.75 | -3.9549 |
| 8 | n-butanol | `CCCCO` | 6026 | 5.56 | 653 | 252.35 | 303.15 | 383.35 | -4.8019 |
| 9 | acetonitrile | `CC#N` | 5511 | 5.09 | 593 | 243.15 | 303.15 | 363.15 | -5.0127 |
| 10 | DMF | `CN(C)C=O` | 2802 | 2.59 | 297 | 268.35 | 303.15 | 383.38 | -3.2471 |
| 11 | toluene | `Cc1ccccc1` | 2750 | 2.54 | 277 | 253.45 | 303.15 | 362.65 | -4.9598 |
| 12 | isobutanol | `CC(C)CO` | 2672 | 2.47 | 287 | 252.65 | 303.15 | 383.35 | -4.6512 |
| 13 | methyl acetate | `COC(C)=O` | 2190 | 2.02 | 247 | 253.15 | 303.15 | 363.15 | -3.9552 |
| 14 | 1,4-dioxane | `C1COCCO1` | 2171 | 2.00 | 262 | 273.15 | 308.15 | 358.35 | -3.8505 |
| 15 | THF | `C1CCOC1` | 1615 | 1.49 | 183 | 253.85 | 303.15 | 338.15 | -3.0769 |
| 16 | 2-butanone | `CCC(C)=O` | 1608 | 1.48 | 166 | 271.23 | 303.15 | 345.25 | -4.0666 |
| 17 | n-pentanol | `CCCCCO` | 1532 | 1.41 | 179 | 272.15 | 303.15 | 363.15 | -4.5962 |
| 18 | sec-butanol | `CCC(C)O` | 1345 | 1.24 | 169 | 253.15 | 303.15 | 363.15 | -4.8685 |
| 19 | n-butyl acetate | `CCCCOC(C)=O` | 1308 | 1.21 | 153 | 273.15 | 303.15 | 363.26 | -4.4112 |
| 20 | n-hexane | `CCCCCC` | 1187 | 1.10 | 192 | 253.15 | 303.15 | 338.15 | -7.4021 |

## Full Solvent Frequency Table

| Rank | Solvent | SMILES | Records | Share (%) | Unique solutes/pairs | T min (K) | T median (K) | T max (K) | Median ln x2 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | ethanol | `CCO` | 10247 | 9.4628 | 1084 | 248.20 | 303.15 | 360.15 | -5.0468 |
| 2 | methanol | `CO` | 8379 | 7.7378 | 907 | 248.20 | 303.15 | 354.15 | -4.8643 |
| 3 | isopropanol | `CC(C)O` | 7532 | 6.9556 | 809 | 252.05 | 303.15 | 363.15 | -5.1898 |
| 4 | ethyl acetate | `CCOC(C)=O` | 7106 | 6.5622 | 776 | 248.20 | 303.15 | 348.15 | -4.2944 |
| 5 | n-propanol | `CCCO` | 6855 | 6.3304 | 720 | 248.20 | 303.15 | 368.15 | -4.8254 |
| 6 | water | `O` | 6524 | 6.0247 | 737 | 273.15 | 305.54 | 373.15 | -7.8248 |
| 7 | acetone | `CC(C)=O` | 6263 | 5.7837 | 688 | 248.20 | 303.15 | 355.75 | -3.9549 |
| 8 | n-butanol | `CCCCO` | 6026 | 5.5648 | 653 | 252.35 | 303.15 | 383.35 | -4.8019 |
| 9 | acetonitrile | `CC#N` | 5511 | 5.0893 | 593 | 243.15 | 303.15 | 363.15 | -5.0127 |
| 10 | DMF | `CN(C)C=O` | 2802 | 2.5876 | 297 | 268.35 | 303.15 | 383.38 | -3.2471 |
| 11 | toluene | `Cc1ccccc1` | 2750 | 2.5395 | 277 | 253.45 | 303.15 | 362.65 | -4.9598 |
| 12 | isobutanol | `CC(C)CO` | 2672 | 2.4675 | 287 | 252.65 | 303.15 | 383.35 | -4.6512 |
| 13 | methyl acetate | `COC(C)=O` | 2190 | 2.0224 | 247 | 253.15 | 303.15 | 363.15 | -3.9552 |
| 14 | 1,4-dioxane | `C1COCCO1` | 2171 | 2.0049 | 262 | 273.15 | 308.15 | 358.35 | -3.8505 |
| 15 | THF | `C1CCOC1` | 1615 | 1.4914 | 183 | 253.85 | 303.15 | 338.15 | -3.0769 |
| 16 | 2-butanone | `CCC(C)=O` | 1608 | 1.4849 | 166 | 271.23 | 303.15 | 345.25 | -4.0666 |
| 17 | n-pentanol | `CCCCCO` | 1532 | 1.4148 | 179 | 272.15 | 303.15 | 363.15 | -4.5962 |
| 18 | sec-butanol | `CCC(C)O` | 1345 | 1.2421 | 169 | 253.15 | 303.15 | 363.15 | -4.8685 |
| 19 | n-butyl acetate | `CCCCOC(C)=O` | 1308 | 1.2079 | 153 | 273.15 | 303.15 | 363.26 | -4.4112 |
| 20 | n-hexane | `CCCCCC` | 1187 | 1.0962 | 192 | 253.15 | 303.15 | 338.15 | -7.4021 |
| 21 | cyclohexane | `C1CCCCC1` | 1141 | 1.0537 | 136 | 273.15 | 303.15 | 343.30 | -6.5932 |
| 22 | ethylene glycol | `OCCO` | 1139 | 1.0518 | 137 | 273.15 | 303.15 | 356.95 | -5.3865 |
| 23 | DMSO | `CS(C)=O` | 1106 | 1.0214 | 138 | 273.20 | 308.17 | 405.07 | -3.2285 |
| 24 | NMP | `CN1CCCC1=O` | 1099 | 1.0149 | 116 | 268.35 | 303.15 | 425.77 | -2.6064 |
| 25 | n-propyl acetate | `CCCOC(C)=O` | 1046 | 0.9660 | 119 | 273.15 | 303.15 | 363.20 | -4.2485 |
| 26 | chloroform | `ClC(Cl)Cl` | 1035 | 0.9558 | 124 | 273.15 | 303.15 | 355.15 | -4.4228 |
| 27 | n-octanol | `CCCCCCCCO` | 1024 | 0.9456 | 169 | 262.78 | 303.15 | 383.15 | -5.3236 |
| 28 | acetic acid | `CC(=O)O` | 810 | 0.7480 | 81 | 278.15 | 313.15 | 400.54 | -4.3420 |
| 29 | dichloromethane | `ClCCl` | 732 | 0.6760 | 110 | 252.95 | 297.10 | 345.00 | -4.2100 |
| 30 | isopropyl acetate | `CC(=O)OC(C)C` | 632 | 0.5836 | 69 | 273.15 | 303.15 | 328.15 | -4.0912 |
| 31 | cyclohexanone | `O=C1CCCCC1` | 615 | 0.5679 | 59 | 272.65 | 303.65 | 370.35 | -3.8291 |
| 32 | isopentanol | `CC(C)CCO` | 596 | 0.5504 | 68 | 272.15 | 301.46 | 343.15 | -4.1708 |
| 33 | DMAc | `CC(=O)N(C)C` | 563 | 0.5199 | 57 | 273.15 | 308.15 | 392.17 | -2.2567 |
| 34 | propylene glycol | `CC(O)CO` | 553 | 0.5107 | 88 | 273.15 | 303.20 | 356.85 | -5.7559 |
| 35 | ethyl formate | `CCOC=O` | 546 | 0.5042 | 58 | 272.05 | 302.60 | 333.15 | -4.0300 |
| 36 | 2-ethoxyethanol | `CCOCCO` | 516 | 0.4765 | 52 | 276.70 | 308.14 | 368.16 | -3.2938 |
| 37 | n-heptane | `CCCCCCC` | 503 | 0.4645 | 59 | 273.15 | 303.15 | 352.45 | -5.0625 |
| 38 | 1,2-dichloroethane | `ClCCCl` | 492 | 0.4543 | 52 | 273.15 | 305.85 | 353.15 | -3.6018 |
| 39 | benzene | `c1ccccc1` | 483 | 0.4460 | 53 | 278.15 | 313.00 | 353.15 | -5.6465 |
| 40 | n-hexanol | `CCCCCCO` | 401 | 0.3703 | 48 | 272.15 | 303.15 | 350.27 | -4.2475 |
| 41 | 2-methoxyethanol | `COCCO` | 389 | 0.3592 | 41 | 276.40 | 303.15 | 333.15 | -2.9648 |
| 42 | isobutyl acetate | `CC(=O)OCC(C)C` | 346 | 0.3195 | 35 | 273.15 | 304.78 | 353.15 | -3.9418 |
| 43 | tetrachloromethane | `ClC(Cl)(Cl)Cl` | 309 | 0.2854 | 38 | 252.55 | 302.75 | 338.05 | -4.7242 |
| 44 | n-pentyl acetate | `CCCCCOC(C)=O` | 235 | 0.2170 | 27 | 273.15 | 303.15 | 333.15 | -3.7169 |
| 45 | n-heptanol | `CCCCCCCO` | 227 | 0.2096 | 26 | 278.00 | 303.15 | 333.15 | -4.3552 |
| 46 | MIBK | `CC(=O)CC(C)C` | 219 | 0.2022 | 24 | 276.45 | 308.15 | 363.15 | -5.6316 |
| 47 | transcutol | `CCOCCOCCO` | 216 | 0.1995 | 42 | 273.20 | 308.15 | 338.15 | -3.5422 |
| 48 | 2-propoxyethanol | `CCCOCCO` | 209 | 0.1930 | 24 | 278.15 | 303.15 | 333.15 | -3.4067 |
| 49 | ethylbenzene | `CCc1ccccc1` | 209 | 0.1930 | 17 | 262.50 | 296.91 | 361.15 | -3.6758 |
| 50 | MTBE | `COC(C)(C)C` | 192 | 0.1773 | 25 | 273.15 | 298.67 | 334.15 | -4.9418 |
| 51 | tert-butanol | `CC(C)(C)O` | 181 | 0.1671 | 25 | 278.15 | 314.95 | 348.15 | -3.4389 |
| 52 | 2-butoxyethanol | `CCCCOCCO` | 169 | 0.1561 | 20 | 278.15 | 303.15 | 333.15 | -3.1352 |
| 53 | dimethyl carbonate | `COC(=O)OC` | 163 | 0.1505 | 18 | 278.15 | 308.15 | 365.15 | -4.5776 |
| 54 | o-xylene | `Cc1ccccc1C` | 162 | 0.1496 | 15 | 273.35 | 313.15 | 361.25 | -4.8962 |
| 55 | 2-pentanone | `CCCC(C)=O` | 161 | 0.1487 | 16 | 272.05 | 298.35 | 333.15 | -3.7381 |
| 56 | formic acid | `O=CO` | 155 | 0.1431 | 16 | 278.15 | 308.15 | 335.50 | -5.0800 |
| 57 | chlorobenzene | `Clc1ccccc1` | 152 | 0.1404 | 27 | 274.85 | 313.15 | 383.15 | -5.2902 |
| 58 | m-xylene | `Cc1cccc(C)c1` | 148 | 0.1367 | 15 | 277.05 | 312.75 | 343.15 | -4.9249 |
| 59 | diethyl ether | `CCOCC` | 141 | 0.1302 | 26 | 254.25 | 293.15 | 307.15 | -4.6684 |
| 60 | propionic acid | `CCC(=O)O` | 135 | 0.1247 | 14 | 278.15 | 308.15 | 338.75 | -4.1414 |
| 61 | p-xylene | `Cc1ccc(C)cc1` | 134 | 0.1237 | 14 | 288.15 | 317.75 | 348.85 | -2.5773 |
| 62 | cyclopentanone | `O=C1CCCC1` | 108 | 0.0997 | 10 | 272.65 | 303.15 | 358.15 | -2.2798 |
| 63 | formamide | `NC=O` | 106 | 0.0979 | 13 | 278.15 | 301.65 | 350.15 | -3.0607 |
| 64 | n-octane | `CCCCCCCC` | 101 | 0.0933 | 14 | 273.15 | 308.15 | 354.15 | -6.7007 |
| 65 | anisole | `COc1ccccc1` | 93 | 0.0859 | 11 | 283.15 | 313.15 | 353.15 | -3.8849 |
| 66 | cyclopentyl methyl ether | `COC1CCCC1` | 92 | 0.0850 | 13 | 283.15 | 321.10 | 353.15 | -3.4269 |
| 67 | pyridine | `c1ccncc1` | 85 | 0.0785 | 8 | 278.55 | 318.15 | 363.15 | -3.7050 |
| 68 | furfural | `O=Cc1ccco1` | 84 | 0.0776 | 7 | 271.10 | 305.27 | 335.75 | -1.0570 |
| 69 | gamma-butyrolactone | `O=C1CCCO1` | 79 | 0.0730 | 7 | 278.15 | 318.15 | 368.55 | -3.2906 |
| 70 | 1-methoxy-2-propanol | `COCC(C)O` | 78 | 0.0720 | 7 | 276.60 | 308.15 | 343.15 | -4.0415 |
| 71 | 3-pentanone | `CCC(=O)CC` | 75 | 0.0693 | 6 | 273.15 | 309.05 | 353.65 | -1.3540 |
| 72 | n-dodecane | `CCCCCCCCCCCC` | 71 | 0.0656 | 8 | 273.15 | 303.20 | 328.20 | -7.9895 |
| 73 | diisopropyl ether | `CC(C)OC(C)C` | 68 | 0.0628 | 13 | 278.15 | 303.15 | 333.15 | -3.3341 |
| 74 | diethylene glycol | `OCCOCCO` | 62 | 0.0573 | 5 | 276.70 | 309.58 | 334.15 | -4.2207 |
| 75 | methylcyclohexane | `CC1CCCCC1` | 62 | 0.0573 | 9 | 278.15 | 318.35 | 350.95 | -3.5651 |
| 76 | isopentyl acetate | `CC(=O)OCCC(C)C` | 59 | 0.0545 | 6 | 278.15 | 303.15 | 328.15 | -2.8797 |
| 77 | tert-amyl alcohol | `CCC(C)(C)O` | 55 | 0.0508 | 9 | 278.15 | 307.15 | 328.15 | -4.3505 |
| 78 | acetylacetone | `CC(=O)CC(C)=O` | 51 | 0.0471 | 5 | 278.15 | 308.15 | 334.65 | -5.6040 |
| 79 | acetophenone | `CC(=O)c1ccccc1` | 50 | 0.0462 | 7 | 289.15 | 318.15 | 344.15 | -6.2644 |
| 80 | methyl propionate | `CCC(=O)OC` | 50 | 0.0462 | 6 | 283.13 | 303.14 | 323.18 | -3.8474 |
| 81 | n-hexadecane | `CCCCCCCCCCCCCCCC` | 50 | 0.0462 | 8 | 293.20 | 308.20 | 328.20 | -8.0821 |
| 82 | n-nonanol | `CCCCCCCCCO` | 48 | 0.0443 | 6 | 293.20 | 310.70 | 328.20 | -5.6979 |
| 83 | trichloroethylene | `ClC=C(Cl)Cl` | 48 | 0.0443 | 5 | 282.00 | 305.52 | 323.75 | -1.6975 |
| 84 | cyclohexanol | `OC1CCCCC1` | 47 | 0.0434 | 4 | 283.10 | 318.15 | 352.95 | -2.1733 |
| 85 | benzyl alcohol | `OCc1ccccc1` | 45 | 0.0416 | 4 | 273.15 | 298.15 | 323.15 | -3.4667 |
| 86 | ethyl lactate | `CCOC(=O)C(C)O` | 45 | 0.0416 | 5 | 278.15 | 303.15 | 323.15 | -2.5688 |
| 87 | 2-ethylhexanol | `CCCCC(CC)CO` | 43 | 0.0397 | 6 | 278.02 | 308.15 | 363.15 | -7.4894 |
| 88 | 2-pentanol | `CCCC(C)O` | 43 | 0.0397 | 9 | 278.15 | 303.15 | 343.26 | -6.4421 |
| 89 | dipropyl ether | `CCCOCCC` | 41 | 0.0379 | 3 | 294.15 | 323.45 | 353.05 | -1.4740 |
| 90 | isooctanol | `CC(C)CCCCCO` | 41 | 0.0379 | 3 | 278.15 | 305.65 | 329.75 | -4.3283 |
| 91 | mesitylene | `Cc1cc(C)cc(C)c1` | 40 | 0.0369 | 5 | 283.15 | 313.15 | 344.15 | -3.0084 |
| 92 | 1,2-dichlorobenzene | `Clc1ccccc1Cl` | 36 | 0.0332 | 4 | 273.15 | 303.15 | 323.35 | -4.6248 |
| 93 | diglyme | `COCCOCCOC` | 35 | 0.0323 | 5 | 278.15 | 313.15 | 353.15 | -4.7253 |
| 94 | propylene carbonate | `CC1COC(=O)O1` | 35 | 0.0323 | 6 | 293.15 | 323.15 | 363.15 | -3.7508 |
| 95 | n-methylformamide | `CNC=O` | 34 | 0.0314 | 4 | 283.15 | 308.15 | 334.35 | -1.6183 |
| 96 | 1-methoxy-2-propyl acetate | `COCC(C)OC(C)=O` | 33 | 0.0305 | 3 | 293.15 | 318.15 | 343.15 | -5.9706 |
| 97 | 1-propoxy-2-propanol | `CCCOCC(C)O` | 33 | 0.0305 | 3 | 293.15 | 318.15 | 343.15 | -6.1370 |
| 98 | 2-(2-methoxypropoxy) propanol | `COC(C)COC(C)COC(C)CO` | 33 | 0.0305 | 3 | 293.15 | 318.15 | 343.15 | -4.9426 |
| 99 | glycerin | `OCC(O)CO` | 33 | 0.0305 | 6 | 288.15 | 303.15 | 323.15 | -7.9807 |
| 100 | n-pentane | `CCCCC` | 33 | 0.0305 | 8 | 278.15 | 293.20 | 303.20 | -8.7883 |
| 101 | ε-caprolactone | `O=C1CCCCCO1` | 30 | 0.0277 | 3 | 286.25 | 309.45 | 334.15 | -3.1739 |
| 102 | p-cymene | `Cc1ccc(C(C)C)cc1` | 29 | 0.0268 | 3 | 296.65 | 323.15 | 348.85 | -0.9314 |
| 103 | morpholine-4-carbaldehyde | `O=CN1CCOCC1` | 28 | 0.0259 | 4 | 293.20 | 308.20 | 328.20 | -4.2233 |
| 104 | epichlorohydrin | `ClCC1CO1` | 27 | 0.0249 | 3 | 283.15 | 323.15 | 353.15 | -3.1646 |
| 105 | gamma-valerolactone | `O=C1CCCOC1` | 26 | 0.0240 | 3 | 283.15 | 320.65 | 353.15 | -4.7623 |
| 106 | 1,1,1-trichloroethane | `CC(Cl)(Cl)Cl` | 25 | 0.0231 | 3 | 287.55 | 300.95 | 318.15 | -2.8630 |
| 107 | 2-aminoethanol | `NCCO` | 24 | 0.0222 | 3 | 293.20 | 310.70 | 328.20 | -4.8284 |
| 108 | sulfolane | `O=S1(=O)CCCC1` | 24 | 0.0222 | 2 | 297.65 | 322.95 | 345.15 | -1.8353 |
| 109 | 2-methyltetrahydrofuran | `CC1CCCO1` | 23 | 0.0212 | 3 | 278.15 | 303.15 | 333.20 | -3.6134 |
| 110 | 2-(2-butoxyethoxy)ethanol | `CCCCOCCOCCO` | 21 | 0.0194 | 2 | 282.75 | 316.05 | 336.15 | -1.2740 |
| 111 | isooctane | `CC(C)CC(C)(C)C` | 21 | 0.0194 | 4 | 283.15 | 306.77 | 341.20 | -3.7550 |
| 112 | n-hexyl acetate | `CCCCCCOC(C)=O` | 21 | 0.0194 | 2 | 278.15 | 308.15 | 332.85 | -2.3482 |
| 113 | 2,2,4-trimethylpentane | `CCC(C)(C)C(C)C` | 20 | 0.0185 | 4 | 293.00 | 305.50 | 323.00 | -4.3945 |
| 114 | decalin | `C1CCC2CCCCC2C1` | 20 | 0.0185 | 2 | 294.15 | 314.10 | 338.65 | -2.9850 |
| 115 | sec-butyl acetate | `CCC(C)OC(C)=O` | 20 | 0.0185 | 2 | 279.10 | 296.65 | 315.50 | -4.2990 |
| 116 | tert-butyl acetate | `CC(=O)OC(C)(C)C` | 20 | 0.0185 | 2 | 279.10 | 296.65 | 315.50 | -4.5424 |
| 117 | isopropyl myristate | `CCCCCCCCCCCCCCC(=O)OC(C)C` | 19 | 0.0175 | 4 | 293.15 | 308.15 | 318.20 | -3.1653 |
| 118 | n-butyric acid | `CCCC(=O)O` | 19 | 0.0175 | 2 | 278.17 | 303.15 | 323.28 | -2.4845 |
| 119 | 1,2-diethoxyethane | `CCOCCOCC` | 18 | 0.0166 | 3 | 293.15 | 318.00 | 343.55 | -5.6492 |
| 120 | acetyl acetate | `CC(=O)OC(C)=O` | 18 | 0.0166 | 2 | 278.45 | 302.15 | 331.70 | -1.6459 |
| 121 | di(2-ethylhexyl) phthalate | `CCCC(CC)COC(=O)c1ccccc1C(=O)OCC(CC)CC` | 18 | 0.0166 | 3 | 312.45 | 348.35 | 398.15 | -2.3208 |
| 122 | ethyl propionate | `CCOC(=O)CC` | 18 | 0.0166 | 2 | 283.15 | 305.65 | 328.15 | -4.5885 |
| 123 | nitromethane | `C[N+](=O)[O-]` | 18 | 0.0166 | 2 | 283.15 | 308.15 | 333.15 | -5.8056 |
| 124 | benzonitrile | `N#Cc1ccccc1` | 16 | 0.0148 | 2 | 283.15 | 305.65 | 323.15 | -2.6273 |
| 125 | 1-bromopropane | `CCCBr` | 15 | 0.0139 | 1 | 280.60 | 301.40 | 313.80 | -0.9061 |
| 126 | trioctyl phosphate | `CCCCCCCCOP(=O)(OCCCCCCCC)OCCCCCCCC` | 15 | 0.0139 | 2 | 303.15 | 319.15 | 344.15 | -1.7779 |
| 127 | 4-methyl-2-pentanol | `CC(C)CC(C)O` | 13 | 0.0120 | 5 | 283.15 | 298.15 | 323.15 | -8.2358 |
| 128 | n-decanol | `CCCCCCCCCCO` | 13 | 0.0120 | 5 | 298.15 | 357.15 | 392.15 | -6.0348 |
| 129 | triethyl phosphate | `CCOP(=O)(OCC)OCC` | 13 | 0.0120 | 1 | 298.15 | 328.15 | 358.15 | -2.6593 |
| 130 | propionitrile | `CCC#N` | 12 | 0.0111 | 4 | 298.15 | 305.65 | 318.15 | -5.5119 |
| 131 | vinylene carbonate | `O=C1OC=CCO1` | 12 | 0.0111 | 1 | 293.15 | 320.65 | 348.15 | -2.9684 |
| 132 | 1,1,2-trichlorotrifluoroethane | `FC(F)(Cl)C(F)(Cl)Cl` | 11 | 0.0102 | 1 | 290.45 | 308.05 | 316.75 | -3.9528 |
| 133 | 1,2-dimethoxyethane | `COCCOC` | 10 | 0.0092 | 2 | 293.15 | 320.65 | 343.15 | -5.4709 |
| 134 | 1,4-butanediol | `OCCCCO` | 10 | 0.0092 | 2 | 293.20 | 303.20 | 313.20 | -4.2830 |
| 135 | 2-hexanone | `CCCCC(C)=O` | 10 | 0.0092 | 1 | 273.15 | 295.65 | 318.15 | -9.9692 |
| 136 | 2-octanol | `CCCCCCC(C)O` | 10 | 0.0092 | 1 | 278.04 | 300.38 | 322.20 | -5.4935 |
| 137 | DMS | `COC(=O)CCC(=O)OC` | 10 | 0.0092 | 1 | 295.55 | 313.20 | 326.35 | -4.1719 |
| 138 | N,N-dimethylaniline | `CN(C)c1ccccc1` | 10 | 0.0092 | 1 | 288.15 | 310.65 | 333.15 | -4.0313 |
| 139 | acrylonitrile | `C=CC#N` | 10 | 0.0092 | 2 | 298.15 | 308.15 | 318.15 | -5.1390 |
| 140 | aniline | `Nc1ccccc1` | 10 | 0.0092 | 1 | 288.05 | 310.80 | 333.35 | -2.9533 |
| 141 | cumene | `CC(C)c1ccccc1` | 10 | 0.0092 | 1 | 278.15 | 300.65 | 323.15 | -5.8659 |
| 142 | diacetone alcohol | `CC(=O)CC(C)(C)O` | 10 | 0.0092 | 1 | 283.15 | 305.65 | 328.15 | -1.1697 |
| 143 | ethyl orthosilicate | `CCO[Si](OCC)(OCC)OCC` | 10 | 0.0092 | 1 | 283.15 | 305.65 | 328.15 | -3.0802 |
| 144 | limonene | `C=C(C)C1CC=C(C)CC1` | 10 | 0.0092 | 2 | 283.00 | 305.70 | 323.00 | -5.5778 |
| 145 | octyl acetate | `CCCCCCCCCOC(C)=O` | 10 | 0.0092 | 1 | 278.15 | 300.65 | 323.15 | -2.7821 |
| 146 | tributyl phosphate | `CCCCOP(=O)(OCCCC)OCCCC` | 10 | 0.0092 | 1 | 283.15 | 305.65 | 328.15 | -0.6015 |
| 147 | 1,1,2,2-tetrachloroethane | `ClC(Cl)C(Cl)Cl` | 9 | 0.0083 | 1 | 288.15 | 308.15 | 328.15 | -9.2512 |
| 148 | 1,1,2-trichloroethane | `ClCC(Cl)Cl` | 9 | 0.0083 | 1 | 278.15 | 298.15 | 318.15 | -4.2457 |
| 149 | 1,3-propanediol | `OCCCO` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -4.6955 |
| 150 | 2-methyl-cyclohexyl acetate | `CC(=O)OC1CCCCC1C` | 9 | 0.0083 | 1 | 304.15 | 324.15 | 344.15 | -1.9338 |
| 151 | 2-phenylethanol | `OCCc1ccccc1` | 9 | 0.0083 | 1 | 304.15 | 324.15 | 344.15 | -1.5597 |
| 152 | acrylic acid | `C=CC(=O)O` | 9 | 0.0083 | 1 | 293.15 | 313.15 | 333.15 | -2.6846 |
| 153 | bromobenzene | `Brc1ccccc1` | 9 | 0.0083 | 1 | 288.15 | 308.15 | 328.15 | -8.1736 |
| 154 | butyl lactate | `CCCCOC(=O)C(C)O` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -3.1133 |
| 155 | dibromomethane | `BrCBr` | 9 | 0.0083 | 1 | 288.15 | 308.15 | 328.15 | -8.6170 |
| 156 | diethyl carbonate | `CCOC(=O)OCC` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -3.3604 |
| 157 | diisobutyl methanol | `CC(C)CC(O)CC(C)C` | 9 | 0.0083 | 1 | 304.15 | 324.15 | 344.15 | -2.3300 |
| 158 | dimethyl sulfate | `COS(=O)(=O)OC` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -4.4741 |
| 159 | dioctyl adipate | `CCCCCCCCOC(=O)CCCCC(=O)OCCCCCCCC` | 9 | 0.0083 | 1 | 304.15 | 324.15 | 344.15 | -2.0479 |
| 160 | ethyl butyrate | `CCCC(=O)OCC` | 9 | 0.0083 | 1 | 288.15 | 308.15 | 328.15 | -3.9937 |
| 161 | methyl 4-tert-butylbenzoate | `COC(=O)c1ccc(C(C)(C)C)cc1` | 9 | 0.0083 | 1 | 293.15 | 313.15 | 333.15 | -2.2818 |
| 162 | methyl lactate | `COC(=O)C(C)O` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -2.9867 |
| 163 | methyl methacrylate | `C=C(C)C(=O)OC` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -4.0473 |
| 164 | morpholine | `C1COCCN1` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -3.5302 |
| 165 | n-dodecanol | `CCCCCCCCCCCCO` | 9 | 0.0083 | 1 | 349.15 | 370.15 | 393.15 | -6.6469 |
| 166 | p-tert-butyltoluene | `Cc1ccc(C(C)(C)C)cc1` | 9 | 0.0083 | 1 | 293.15 | 313.15 | 333.15 | -3.2888 |
| 167 | propanediol butyl ether | `CCCCOCC(O)CO` | 9 | 0.0083 | 1 | 283.15 | 303.15 | 323.15 | -5.5911 |
| 168 | styrene | `C=Cc1ccccc1` | 9 | 0.0083 | 1 | 304.15 | 324.15 | 344.15 | -1.7054 |
| 169 | tert-butylamine | `CC(C)(C)N` | 9 | 0.0083 | 1 | 273.20 | 293.20 | 313.20 | -2.0025 |
| 170 | tetrabutyl urea | `CCCCN(CCCC)C(=O)N(CCCC)CCCC` | 9 | 0.0083 | 1 | 304.15 | 324.15 | 344.15 | -2.1533 |
| 171 | triethyl orthoformate | `CCOC(OCC)OCC` | 9 | 0.0083 | 1 | 278.15 | 298.15 | 318.15 | -3.0514 |
| 172 | cyrene | `O=C1C2CCOC1C(CO)C2` | 8 | 0.0074 | 1 | 284.00 | 296.75 | 332.00 | -6.7185 |
| 173 | dimethoxymethane | `COCOC` | 8 | 0.0074 | 1 | 288.15 | 301.65 | 312.15 | -0.7553 |
| 174 | ethylene carbonate | `O=C1OCCCO1` | 8 | 0.0074 | 1 | 313.15 | 330.65 | 348.15 | -3.2982 |
| 175 | 1,2,4-trichlorobenzene | `Clc1ccc(Cl)c(Cl)c1` | 7 | 0.0065 | 1 | 293.75 | 308.45 | 323.15 | -3.9206 |
| 176 | 2-ethoxyethyl acetate | `CCOCCOC(C)=O` | 7 | 0.0065 | 1 | 278.15 | 303.15 | 333.15 | -2.6967 |
| 177 | 2-ethylhexyl acetate | `CCC(CC)COC(C)=O` | 7 | 0.0065 | 1 | 283.15 | 298.15 | 313.15 | -4.4063 |
| 178 | 4-methylpyridine | `Cc1ccncc1` | 7 | 0.0065 | 1 | 299.65 | 311.65 | 327.45 | -3.5217 |
| 179 | dibutyl ether | `CCCCOCCCC` | 7 | 0.0065 | 7 | 293.15 | 298.15 | 298.20 | -4.6367 |
| 180 | furan | `c1ccoc1` | 7 | 0.0065 | 1 | 278.55 | 288.25 | 297.25 | -2.6838 |
| 181 | 2,6-dimethyl-4-heptanol | `CC(C)CC(O)CC(C)C` | 6 | 0.0055 | 1 | 303.15 | 315.65 | 333.15 | -2.9168 |
| 182 | DEF | `CCN(C=O)CC` | 6 | 0.0055 | 1 | 298.35 | 332.55 | 367.45 | -2.3391 |
| 183 | cyclohexylamine | `NC1CCCCC1` | 6 | 0.0055 | 1 | 287.25 | 325.25 | 366.15 | -3.4991 |
| 184 | dimethyl isosorbide | `COCC1OC2OCCC2C1OC` | 6 | 0.0055 | 1 | 282.60 | 303.60 | 330.90 | -7.3990 |
| 185 | 1,1-dichloroethane | `CC(Cl)Cl` | 5 | 0.0046 | 1 | 288.15 | 298.15 | 308.15 | -18.4332 |
| 186 | 2-methyl-1-pentanol | `CCC(C)CCO` | 5 | 0.0046 | 5 | 298.15 | 298.15 | 298.20 | -3.4405 |
| 187 | eugenol | `C=CCc1ccc(O)c(OC)c1` | 5 | 0.0046 | 1 | 298.20 | 308.20 | 318.20 | -7.8494 |
| 188 | span 80 | `CCCCCCCC=CCCCCCCCC(=O)O[C@@H]1[C@H](O)[C@H](CO)OC[C@H]1O` | 5 | 0.0046 | 1 | 298.20 | 308.20 | 318.20 | -7.1435 |
| 189 | tetrachloroethylene | `ClC(Cl)=C(Cl)Cl` | 5 | 0.0046 | 1 | 297.25 | 301.95 | 309.75 | -7.6009 |
| 190 | triacetin | `CC(=O)OCC(COC(C)=O)OC(C)=O` | 5 | 0.0046 | 1 | 298.20 | 308.20 | 318.20 | -7.2363 |
| 191 | 2,4-dimethylphenol | `Cc1ccc(O)c(C)c1` | 4 | 0.0037 | 1 | 298.15 | 305.65 | 313.15 | -3.3838 |
| 192 | 2-methyl-1-butanol | `CCC(C)CO` | 4 | 0.0037 | 4 | 298.15 | 298.15 | 298.20 | -3.4419 |
| 193 | methyl formate | `COC=O` | 4 | 0.0037 | 1 | 278.20 | 285.70 | 298.20 | -8.3627 |
| 194 | tetraglyme | `COCCOCCOCCOCCOC` | 4 | 0.0037 | 1 | 298.15 | 305.65 | 313.15 | -2.2432 |
| 195 | triglyme | `COCCOCCOCCOC` | 4 | 0.0037 | 1 | 298.15 | 305.65 | 313.15 | -3.6436 |
| 196 | 2-isopropoxyethanol | `CC(C)OCCO` | 2 | 0.0018 | 2 | 298.15 | 298.17 | 298.20 | -3.2162 |
| 197 | 3,7-dimethyl-1-octanol | `CC(C)CCCC(C)CCO` | 2 | 0.0018 | 2 | 298.15 | 298.15 | 298.15 | -3.7753 |
| 198 | butyronitrile | `CCCC#N` | 2 | 0.0018 | 2 | 298.15 | 298.15 | 298.15 | -1.4254 |
| 199 | methyl butyrate | `CCCC(=O)OC` | 2 | 0.0018 | 2 | 298.15 | 298.15 | 298.15 | -3.8821 |
| 200 | n-decane | `CCCCCCCCCC` | 2 | 0.0018 | 2 | 298.15 | 298.15 | 298.15 | -4.1797 |
| 201 | 1-chlorooctane | `CCCCCCCCCl` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -6.0240 |
| 202 | 1-chlorotetradecane | `CCCCCCCCCCCCCCl` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -6.0323 |
| 203 | 1-hexene | `C=CCCCC` | 1 | 0.0009 | 1 | 293.15 | 293.15 | 293.15 | -8.5844 |
| 204 | 2,2,2-trifluoroethanol | `OC(F)(F)F` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -3.3467 |
| 205 | 3-methoxy-1-butanol | `COC(C)CCO` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -2.9892 |
| 206 | chlorocyclohexane | `ClC1CCCCC1` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -5.8396 |
| 207 | cyclooctane | `C1CCCCCCC1` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -3.3237 |
| 208 | cyclopentanol | `OC1CCCC1` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -2.8154 |
| 209 | n-nonane | `CCCCCCCCC` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -3.6825 |
| 210 | tert-amyl methyl ether | `CCC(C)(C)OC` | 1 | 0.0009 | 1 | 293.15 | 293.15 | 293.15 | -8.6226 |
| 211 | tert-butylcyclohexane | `CC(C)(C)C1CCCCC1` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -3.4963 |
| 212 | tetrahydropyran | `C1CCOCC1` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -4.5815 |
| 213 | undecane | `CCCCCCCCCCC` | 1 | 0.0009 | 1 | 298.15 | 298.15 | 298.15 | -3.5288 |

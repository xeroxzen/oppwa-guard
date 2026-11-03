# Result codes

OPPWA result codes have the form `ddd.ddd.ddd`. [`classify`](api.md#classify) matches them against the patterns below, in this order, and returns the first match.

| Order | Outcome | Pattern | Examples |
|---|---|---|---|
| 1 | `TEST_MODE_SUCCESS` | `^000\.100\.1` | `000.100.110`, `000.100.112` |
| 2 | `SUCCESS` | `^(000\.000\.\|000\.[36]\|000\.400\.1[12]0\|000\.500\.)` | `000.000.000`, `000.400.110` |
| 3 | `SUCCESS_NEEDS_REVIEW` | `^(000\.400\.0[^3]\|000\.400\.100)` | `000.400.000`, `000.400.100` |
| 4 | `PENDING` | `^(000\.200\|800\.400\.5\|100\.400\.500)` | `000.200.000`, `000.200.100`, `800.400.500` |
| 5 | `REJECTED` | anything else | `000.400.030`, `100.396.101`, `800.100.151` |

Test mode is checked first and kept separate from success on purpose. A production integration that fulfils on `000.100.110` is shipping goods for payments that never settle.

## Codes you'll see in a normal flow

| Code | Meaning | Outcome |
|---|---|---|
| `000.200.100` | Checkout successfully created | `PENDING` |
| `000.200.000` | Transaction pending | `PENDING` |
| `000.000.000` | Transaction succeeded | `SUCCESS` |
| `000.100.110` | Request successfully processed in integrator test mode | `TEST_MODE_SUCCESS` |

## Acquirer-specific codes

The patterns follow the public OPPWA result-code reference. Some acquirers add codes of their own. If yours documents a success code that `classify` returns as `REJECTED`, the safe failure is what you get: the order isn't fulfilled. [Open an issue](https://github.com/xeroxzen/oppwa-guard/issues) with a link to the acquirer's documentation.

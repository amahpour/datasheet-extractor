| C3 | C2 | C1 | C0 | A3 | A2 | A1 | A0 | DESCRIPTION |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Write Sequences | Write Sequences | Write Sequences | Write Sequences | Write Sequences | Write Sequences | Write Sequences | Write Sequences | Write Sequences |
| 0 | 0 | 0 | 0 | A3 | A2 | A1 | A0 | Write to DAC input register channel n |
| 0 | 0 | 0 | 1 | A3 | A2 | A1 | A0 | Select to update DAC register channel n |
| 0 | 0 | 1 | 0 | A3 | A2 | A1 | A0 | Write to DAC input register channel n, and update all DAC registers (global software LDAC) |
| 0 | 0 | 1 | 1 | A3 | A2 | A1 | A0 | Write to DAC input register channel n, and update DAC register channel n |
| 0 | 1 | 0 | 0 | X | X | X | X | Power down/on DAC |
| 0 | 1 | 0 | 1 | X | X | X | X | Write to clear code register |
| 0 | 1 | 1 | 0 | X | X | X | X | Write to LDAC register |
| 0 | 1 | 1 | 1 | X | X | X | X | Software reset |
| Read Sequences | Read Sequences | Read Sequences | Read Sequences | Read Sequences | Read Sequences | Read Sequences | Read Sequences | Read Sequences |
| 0 | 0 | 0 | 0 | A3 | A2 | A1 | A0 | Read from DAC input register channel n |
| 0 | 0 | 0 | 1 | A3 | A2 | A1 | A0 | Read from DAC register channel n |
| 0 | 1 | 0 | 0 | X | X | X | X | Read from DAC power down register |
| 0 | 1 | 0 | 1 | X | X | X | X | Read from clear code register |
| 0 | 1 | 1 | 0 | X | X | X | X | Read from LDAC register |
| Access Sequences | Access Sequences | Access Sequences | Access Sequences | Access Sequences | Access Sequences | Access Sequences | Access Sequences | Access Sequences |
| C3 | C2 | C1 | C0 | 0 | 0 | 0 | 0 | DAC channel A |
| C3 | C2 | C1 | C0 | 0 | 0 | 0 | 1 | DAC channel B |
| C3 | C2 | C1 | C0 | 0 | 0 | 1 | 0 | DAC channel C |
| C3 | C2 | C1 | C0 | 0 | 0 | 1 | 1 | DAC channel D |
| C3 | C2 | C1 | C0 | 0 | 1 | 0 | 0 | DAC channel E |
| C3 | C2 | C1 | C0 | 0 | 1 | 0 | 1 | DAC channel F |
| C3 | C2 | C1 | C0 | 0 | 1 | 1 | 0 | DAC channel G |
| C3 | C2 | C1 | C0 | 0 | 1 | 1 | 1 | DAC channel H |
| C3 | C2 | C1 | C0 | 1 | 1 | 1 | 1 | All DAC channels, broadcast update |

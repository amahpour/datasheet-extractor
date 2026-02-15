| C3 | COMMAND AND ACCESS BYTE.C2 | COMMAND AND ACCESS BYTE.C1 | COMMAND AND ACCESS BYTE.C0 | COMMAND AND ACCESS BYTE.A3 | COMMAND AND ACCESS BYTE.A2 | COMMAND AND ACCESS BYTE.A1 | COMMAND AND ACCESS BYTE.A0 | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | MOST SIGNIFICANT DATA BYTE.DATA[7:0] | LEAST SIGNIFICANT DATA BYTE.X | LEAST SIGNIFICANT DATA BYTE.X | LEAST SIGNIFICANT DATA BYTE.X | LEAST SIGNIFICANT DATA BYTE.X | LEAST SIGNIFICANT DATA BYTE. | LEAST SIGNIFICANT DATA BYTE.X X | LEAST SIGNIFICANT DATA BYTE.X | LEAST SIGNIFICANT DATA BYTE.X | LEAST SIGNIFICANT DATA BYTE. | DESCRIPTION.General data format for 8-bit DAC5578 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C3 | C2 | C1 | C0 | A3 A2 |  | A1 | A0 DATA[9:2] | A0 DATA[9:2] | A0 DATA[9:2] | A0 DATA[9:2] | A0 DATA[9:2] | A0 DATA[9:2] | A0 DATA[9:2] | A0 DATA[9:2] | D1 | D0 | X |  | X | X | X | X | X | General data format for 10-bit DAC6578 |
| C3 | C2 | C1 | C0 | A3 A2 |  | A1 | A0 DATA[11:4] | A0 DATA[11:4] | A0 DATA[11:4] | A0 DATA[11:4] | A0 DATA[11:4] | A0 DATA[11:4] | A0 DATA[11:4] | A0 DATA[11:4] | D3 |  | D2 | D1 |  | D0 X X | X | X |  | General data format for 12-bit DAC7578 |
| 0 | 0 | 1 | 1 | 1 | X | X | X | X | X | X | X | X | X X | X | X | X | X | X |  | X X | X | X |  | Invalid code, no action performed |
| 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  |  | X | X | X |  | X |  | Broadcast mode, write to all input registers and update all DAC registers |
| Write to Selected DAC Input Register and Update All DAC Registers (Global Software LDAC) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  | X |  |  | X | X | X | Write to | DAC input register for channel A and update all DAC registers |
| 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  |  | X | X |  | X | X |  | Write to DAC input register for channel B and update all DAC registers |
| 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  |  | X | X X |  | X |  | Write to | DAC input register for channel C and update all DAC registers |
| 0 | 0 | 1 | 0 | 0 | 0 | 1 | 1 |  |  |  | Data[11:4] |  |  |  |  | Data[3:0] | X |  | X | X | X |  | DAC | Write to DAC input register for channel D and update all registers |
| 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |  |  |  | Data[11:4] |  |  |  |  | Data[3:0] | X |  | X |  | X |  | X | Write to DAC input register for channel E and update all DAC registers |
| 0 | 0 | 1 | 0 | 0 | 1 | 0 | 1 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  | X |  | X |  | X |  | X | Write to DAC input register for channel F and update all DAC registers |
| 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  |  |  | X X | X | X |  |  | Write to DAC input register for channel G and update all DAC registers |
| 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 |  |  |  | Data[11:4] |  |  |  | Data[3:0] |  |  | X | X |  | X |  | X | Write to DAC input register for channel H and update all DAC registers |
| 0 | 0 | 1 | 0 | 1 X |  | X | X | X | X | X | X | X | X X | X | X | X | X | X | X | X | X |  | X | Invalid code, no action performed |
| 0 |  | 0 1 | 0 | 1 | 1 | 1 | 1 |  |  |  | Data[11:4] |  |  |  |  |  | Data[3:0] |  | X | X | X |  | X | Broadcast mode, write to all input registers and update all DAC registers |
| Power-Down Register |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 0 | 1 | 0 | 0 | X | X | X | X | X | PD1 | PD0 | DAC | H DAC G | DAC F DAC | E DAC | D DAC | C DAC B |  | DAC A | X | X X | X |  | X |  |
| 0 | 1 |  | 0 | 0 X | X | X | X | X | 0 | 0 | DAC H | DAC G | DAC F DAC | E DAC | D DAC | C | DAC B | DAC A | X | X X | X |  | X | Each DAC bit set to '1' powers on selected DACs Each DAC bit set to '1' powers down selected DACs. |
| 0 |  | 1 | 0 | 0 X | X | X | X | X | 0 | 1 | DAC H | DAC G | DAC F DAC | E DAC | D | DAC C DAC | B DAC A | X | X | X | X |  | X | V OUT connected to GND through 1k Ω pull-down resistor |
| 0 | 1 | 0 | 0 | X | X | X | X | X | 1 | 0 | DAC H | DAC G | DAC F DAC | E DAC D | DAC C | DAC B | DAC A | X |  | X X | X |  | X | Each DAC bit set to '1' powers down selected DACs. V OUT connected to GND through 100k Ω pull-down resistor |
| 0 | 1 |  | 0 | 0 X | X | X X |  | X | 1 | 1 | DAC H | DAC G | DAC F DAC | E DAC | D DAC | C DAC B | DAC A | X |  | X X | X |  | X | Each DAC bit set to '1' powers down selected DACs. V OUT is High Z |
| Clear Code Register |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 0 | 1 | 0 | 1 | X | X | X | X | X | X | X | X | X | X X | X | X |  | X | CL1 | CL0 | X X | X | X |  |  |
| 0 | 1 |  | 0 | 1 X | X | X | X | X | X | X X |  | X | X X |  | X | X | X | 0 | 0 | X X | X |  | X | Write to clear code register, CLR pin clears to zero scale |
| 0 | 1 |  | 0 | 1 X | X |  | X | X | X | X | X | X | X X | X |  | X | 0 | 1 | X | X | X | X |  | Write to clear code register, CLR pin clears to midscale |
| 0 | 1 |  | 0 | 1 X | X | X X | X | X | X | X X |  | X | X X | X | X X | X |  | 1 | 0 | X | X | X | X | Write to clear code register, CLR pin clears to full scale |
| 0 | LDAC | 1 Register | 0 | 1 X | X X | X |  | X | X | X X |  | X | X X | X | X | X | 1 | 1 | X Write to clear code register | X | X X |  |  | disables CLR pin |

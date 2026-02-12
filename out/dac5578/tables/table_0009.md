| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MSB | ··· | LSB | ACK | MSB | ··· | MSB | ··· | LSB | ACK | MSB | ··· | LSB | ACK |
| Address (A) Byte | Address (A) Byte | Address (A) Byte | ACK | ACK Command/Access Byte | ACK Command/Access Byte | MSDB | MSDB | MSDB | ACK | LSDB | LSDB | LSDB | ACK |
| DB[32:24] | DB[32:24] | DB[32:24] | ACK | DB[23:16] | DB[23:16] | DB[15:8] | DB[15:8] | DB[15:8] | ACK | DB[7:0] | DB[7:0] | DB[7:0] | ACK |

# comp3010a2
## COMP3010 Assignment 2: Live chat
### Part 1:

**Usage**

- Run `python3 ws_chat_client.py owl.cs.umanitoba.ca 8001 {role} {verbose} {timeout}`

*where*

| {role} *(required)* | {verbose} *(optional)* | {timeout} *(optional)* |
|---|---|---|
| `consumer`, `producer`, `both` | `-v` | `-t {number}` |

- Example
```
python3 ws_chat_client.py owl.cs.umanitoba.ca 8001 both

python3 ws_chat_client.py owl.cs.umanitoba.ca 8001 consumer -v

python3 ws_chat_client.py owl.cs.umanitoba.ca 8001 producer -t 300

python3 ws_chat_client.py owl.cs.umanitoba.ca 8001 both -v -t 120
```

**Close the program**
- Press `Ctrl + C`

---

### **_*Note:_**
- *-v won't do anything since I left it untouched*
- *Text color of some print statements has been changed to mimic `wscat`*
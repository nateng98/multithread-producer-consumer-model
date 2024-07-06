# Live chat
## owl.cs.umanitoba.ca server is down after June 14, 2024. There is `ws_chat_test_server.py` that runs server on your local machine to test `ws_chat_client.py` out

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

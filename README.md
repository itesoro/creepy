# Creepy

Creepy, or **C**all **REE**mote **PY**thon, is a lightweight library for secure remote procedure calls (RPC) from trusted callers. It enables seamless execution of Python code across different machines or processes with a focus on security.

## Features

### Core Functionality

- **Secure Remote Procedure Calls**: Execute Python functions on remote servers with end-to-end encryption
- **Proxy Objects**: Transparent interaction with remote objects as if they were local
- **Secure Communication**: Encrypted channels using ChaCha20Poly1305 and asymmetric key exchange
- **Session Management**: Persistent connections with automatic session handling
- **Memory Protection**: Secure storage for sensitive data with protections against memory leakage

### Security Features

- **SecureString**: Memory-protected string implementation for sensitive data
- **Memory Locking**: Prevent sensitive data from being swapped to disk
- **Secure Channels**: Encrypted communication between client and server
- **Key Exchange**: Secure handshake protocol for establishing trusted connections

### Utilities

- **Process Isolation**: Run code in separate processes for improved security
- **Module Import**: Import and use remote modules as if they were local
- **Subprocess Execution**: Securely execute Python code in subprocesses

## Usage Examples

### Basic Remote Execution

```python
import creepy

# Connect to a remote server
with creepy.connect('localhost:8000') as remote:
    # Access global scope on the remote server
    scope = remote.globals
    
    # Set variables in the remote scope
    scope.world = 'World!!!'
    
    # Call functions in the remote scope
    scope.print('Hello', scope.world)
```

### Secure Subprocess Execution

```python
from creepy.subprocess import Pypen

# Create a secure subprocess with the specified script
with Pypen(['my_script']) as process:
    # Compile interface to get proxy for remote functions
    proxy = process.compile()
    
    # Call remote function and get result
    result = proxy.my_function(arg1, arg2)
```

### Working with SecureString

```python
from creepy.types import SecureString

# Create a secure string that protects sensitive data in memory
password = SecureString()
for c in "my_secret_password":
    password.append(c)

# Use the secure string with context manager to access in-memory value
with password as password_bytes:
    # Use password_bytes for authentication or encryption
    # Memory is automatically wiped when context manager exits
```

### Copying Files

```python
import creepy

# Copy files between local and remote systems
source_node, source_path = remote1, "/path/on/remote1/file.txt"
dest_node, dest_path = remote2, "/path/on/remote2/file.txt"

# Copy from source to destination
creepy.copy((source_node, source_path), (dest_node, dest_path))
```

## Server Setup

To run a Creepy server:

```bash
creepy run --host 0.0.0.0 --port 8000
```

Or programmatically:

```python
import uvicorn
from creepy import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Advanced Features

### Memory Protection

Creepy provides utilities to protect sensitive data in memory:

```python
from creepy.utils.memory import secret_bytes_are_leaked
from creepy.types import SecureString

# Check if a secret is visible in process memory
password = SecureString()
for c in "secret":
    password.append(c)

# Will return True if the secret is leaked, False otherwise
is_leaked = secret_bytes_are_leaked(password)
```

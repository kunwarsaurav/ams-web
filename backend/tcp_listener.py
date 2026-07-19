import socket
import threading
import os

def handle_client(client_socket, address):
    print(f"\n[+] Connection from {address} established!")
    try:
        while True:
            # Receive up to 4096 bytes from the device
            data = client_socket.recv(4096)
            if not data:
                break
            
            print(f"[{address}] Raw Data Received:")
            print("-" * 40)
            
            # Try to decode as text, if it fails, print the raw bytes/hex
            try:
                decoded_data = data.decode('utf-8')
                print(decoded_data)
            except UnicodeDecodeError:
                print(f"Hex: {data.hex()}")
                print(f"Raw Bytes: {data}")
            
            print("-" * 40)
            
            # Note: We aren't sending a response yet because we don't know what it expects!
            # If it's HTTP, we might need to send a 200 OK. We'll find out.
            
    except Exception as e:
        print(f"[-] Error handling client {address}: {e}")
    finally:
        print(f"[-] Connection closed for {address}")
        client_socket.close()

def start_server(host='0.0.0.0'):
    port = int(os.environ.get("TCP_PORT", 7005))
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"[*] Listening for PCTEL device connections on {host}:{port}...")

    try:
        while True:
            client_sock, addr = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_sock, addr))
            client_handler.start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down listener...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()

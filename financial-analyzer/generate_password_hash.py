import hashlib

# Password Hash Generator for Authentication
# Use this to generate secure password hashes for your clients

def generate_password_hash(password):
    """Generate SHA256 hash for a password"""
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == "__main__":
    print("🔐 Password Hash Generator")
    print("=" * 50)
    
    while True:
        password = input("\nEnter password (or 'quit' to exit): ")
        
        if password.lower() == 'quit':
            break
            
        hash_value = generate_password_hash(password)
        print(f"\nPassword: {password}")
        print(f"SHA256 Hash: {hash_value}")
        print("\nAdd this to your secrets.toml:")
        print(f'username = "{hash_value}"')

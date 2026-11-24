from auth.security import hash_password, verify_password

password = "TestPassword123!"
hashed = hash_password(password)

print("Hash:", hashed)
print("Correct password:", verify_password(password, hashed))
print("Incorrect password:", verify_password("wrongpassword", hashed))
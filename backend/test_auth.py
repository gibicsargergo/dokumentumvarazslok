from auth.store import AuthStore

store = AuthStore()

user = store.create_user(
    email="test@example.com",
    password_hash="temporary-test-hash"
)

print(user)
print(store.get_user_by_email("test@example.com"))
print(store.get_user_by_id(user.id))
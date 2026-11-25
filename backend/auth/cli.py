
import argparse

from .store import AuthStore

def main() -> None:
    parser = argparse.ArgumentParser(
        description="User administration CLI"
    )

    parser.add_argument(
        "email",
        help="Email address of the user",
    )

    parser.add_argument(
        "role",
        choices=["user", "admin"],
        help="New role of the user",
    )

    args = parser.parse_args()

    store = AuthStore()
    user = store.get_user_by_email(args.email)

    if user is None:
        parser.exit(1, "User not found.\n")

    if not store.set_user_role(user.id, args.role):
        parser.exit(1, "Failed to update user role.\n")

    print(f"Role of {user.email} changed to {args.role}.")


if __name__ == "__main__":
    main()

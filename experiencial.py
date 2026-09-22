import json
import os

FILE = "contacts.json"


# Load contacts
def load_contacts():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return []


# Save contacts
def save_contacts(contacts):
    with open(FILE, "w") as f:
        json.dump(contacts, f, indent=4)


# Add contact
def add_contact(contacts):
    name = input("Enter name: ")
    phone = input("Enter phone: ")
    email = input("Enter email: ")

    contacts.append({
        "name": name,
        "phone": phone,
        "email": email
    })

    save_contacts(contacts)
    print("Contact added successfully!")


# Display contacts
def display_contacts(contacts):
    if not contacts:
        print("No contacts found.")
        return

    for i, c in enumerate(contacts, 1):
        print(f"\nContact {i}")
        print("Name :", c["name"])
        print("Phone:", c["phone"])
        print("Email:", c["email"])


# Search contact
def search_contact(contacts):
    key = input("Enter name or phone to search: ").lower()

    found = False

    for c in contacts:
        if key in c["name"].lower() or key in c["phone"]:
            print("\nName :", c["name"])
            print("Phone:", c["phone"])
            print("Email:", c["email"])
            found = True

    if not found:
        print("Contact not found.")


# Update contact
def update_contact(contacts):
    name = input("Enter name of contact to update: ").lower()

    for c in contacts:
        if c["name"].lower() == name:
            c["phone"] = input("Enter new phone: ")
            c["email"] = input("Enter new email: ")
            save_contacts(contacts)
            print("Contact updated successfully!")
            return

    print("Contact not found.")


# Delete contact
def delete_contact(contacts):
    name = input("Enter name of contact to delete: ").lower()

    for c in contacts:
        if c["name"].lower() == name:
            contacts.remove(c)
            save_contacts(contacts)
            print("Contact deleted successfully!")
            return

    print("Contact not found.")


# Main program
contacts = load_contacts()

while True:
    print("\n===== CONTACT BOOK =====")
    print("1. Add Contact")
    print("2. Display Contacts")
    print("3. Search Contact")
    print("4. Update Contact")
    print("5. Delete Contact")
    print("6. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        add_contact(contacts)
    elif choice == "2":
        display_contacts(contacts)
    elif choice == "3":
        search_contact(contacts)
    elif choice == "4":
        update_contact(contacts)
    elif choice == "5":
        delete_contact(contacts)
    elif choice == "6":
        print("Thank you!")
        break
    else:
        print("Invalid choice. Try again.")
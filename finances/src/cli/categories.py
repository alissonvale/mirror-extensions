"""CLI handlers for category CRUD and transaction categorization (US-09).

Two subcommands registered separately:

  categories [list | add | remove]
  categorize <transaction-id> <category-id-or-name> [--type <type>]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.store import (
    get_category,
    get_category_by_name,
    list_categories,
)
from src.store_writes import (
    VALID_CATEGORY_TYPES,
    assign_category_to_transaction,
    create_category,
    delete_category,
    get_or_create_category,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


# --- categories ----------------------------------------------------------


def cmd_categories(api: "ExtensionAPI", args: list[str]) -> int:
    """Manage transaction categories."""
    sub = args[0] if args else "list"
    rest = args[1:] if args else []

    if sub in {"--help", "-h", "help"}:
        _print_categories_usage()
        return 0
    if sub == "list":
        return _cmd_list(api, rest)
    if sub == "add":
        return _cmd_add(api, rest)
    if sub == "remove":
        return _cmd_remove(api, rest)

    if sub.startswith("--"):
        return _cmd_list(api, args)
    print(f"unknown subcommand 'categories {sub}'")
    _print_categories_usage()
    return 1


def _print_categories_usage() -> None:
    print(
        "usage:\n"
        "  python -m memory ext finances categories [list]\n"
        "  python -m memory ext finances categories add <name> <type>"
        f"   (type in: {', '.join(sorted(VALID_CATEGORY_TYPES))})\n"
        "  python -m memory ext finances categories remove <category_id>"
    )


def _cmd_list(api: "ExtensionAPI", _rest: list[str]) -> int:
    cats = list_categories(api)
    if not cats:
        print("(no categories)")
        return 0
    print(f"{'ID':<10}  {'Type':<10}  Name")
    for cat in cats:
        print(f"{cat.id:<10}  {cat.type:<10}  {cat.name}")
    return 0


def _cmd_add(api: "ExtensionAPI", rest: list[str]) -> int:
    if len(rest) < 2:
        print("error: add requires <name> <type>")
        _print_categories_usage()
        return 1
    name, type_ = rest[0], rest[1]
    try:
        cat_id = create_category(api, name=name, type=type_)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    print(f"added category {cat_id}: {name} ({type_})")
    return 0


def _cmd_remove(api: "ExtensionAPI", rest: list[str]) -> int:
    if not rest:
        print("error: remove requires <category_id>")
        _print_categories_usage()
        return 1
    cat_id = rest[0]
    try:
        removed = delete_category(api, cat_id)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    if removed:
        print(f"removed category {cat_id}")
        return 0
    print(f"error: no category with id '{cat_id}'")
    return 1


# --- categorize ----------------------------------------------------------


def cmd_categorize(api: "ExtensionAPI", args: list[str]) -> int:
    """Attach a category to a transaction.

    The category argument can be an id (resolves directly) or a name
    (resolves by case-insensitive lookup; with ``--type <t>``, an
    unknown name is auto-created with that type).
    """
    if args and args[0] in {"--help", "-h", "help"}:
        _print_categorize_usage()
        return 0
    if len(args) < 2:
        print("error: categorize requires <transaction_id> <category>")
        _print_categorize_usage()
        return 1

    txn_id = args[0]
    cat_arg = args[1]
    rest = args[2:]

    auto_type: str | None = None
    if rest:
        if rest[0] != "--type" or len(rest) < 2:
            print(f"error: unrecognised arguments {rest}")
            _print_categorize_usage()
            return 1
        auto_type = rest[1]

    # Resolve the category: try id first, then name.
    category = get_category(api, cat_arg) or get_category_by_name(api, cat_arg)
    if category is None:
        if auto_type is None:
            print(
                f"error: no category matches '{cat_arg}'. Create it first "
                "or pass --type <income|expense|transfer> to auto-create."
            )
            return 1
        try:
            cat_id = get_or_create_category(
                api, name=cat_arg, type=auto_type
            )
        except ValueError as exc:
            print(f"error: {exc}")
            return 1
        category_id = cat_id
    else:
        category_id = category.id

    # Verify the transaction exists with a cheap read.
    row = api.read(
        "SELECT id FROM ext_finances_transactions WHERE id = ?",
        (txn_id,),
    ).fetchone()
    if not row:
        print(f"error: no transaction with id '{txn_id}'")
        return 1

    changed = assign_category_to_transaction(
        api, transaction_id=txn_id, category_id=category_id
    )
    if changed:
        print(f"categorized transaction {txn_id} as {category_id}")
        return 0
    print(f"error: could not update transaction {txn_id}")
    return 1


def _print_categorize_usage() -> None:
    print(
        "usage: python -m memory ext finances categorize "
        "<transaction_id> <category-id-or-name> [--type <type>]"
    )

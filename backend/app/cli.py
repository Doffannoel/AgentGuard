import argparse
import getpass
from decimal import Decimal

from sqlalchemy import select

from .auth import passwords
from .db import SessionLocal
from .models import ModelPricing, Tenant, TenantMember, User


def main():
    parser = argparse.ArgumentParser(description="AgentGuard operator commands")
    commands = parser.add_subparsers(dest="command", required=True)
    user_parser = commands.add_parser("create-admin")
    user_parser.add_argument("--email", required=True)
    user_parser.add_argument("--tenant", required=True)
    price_parser = commands.add_parser("set-price")
    price_parser.add_argument("--provider", required=True, choices=["Mock", "OpenAI", "Ollama"])
    price_parser.add_argument("--model", required=True)
    price_parser.add_argument("--input", required=True, type=Decimal)
    price_parser.add_argument("--output", required=True, type=Decimal)
    seed_parser = commands.add_parser("seed-demo", help="Create sample data for an existing administrator")
    seed_parser.add_argument("--email", required=True)
    args = parser.parse_args()
    if args.command == "seed-demo":
        from .db import engine
        from .seed import seed_demo

        try:
            project_id, created = seed_demo(engine, args.email)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"{'Created' if created else 'Already seeded'}: Demo Seeder /projects/{project_id}")
        return
    with SessionLocal() as db:
        if args.command == "create-admin":
            email = args.email.strip().lower()
            if db.scalar(select(User).where(User.email == email)):
                parser.error("User already exists")
            password = getpass.getpass("Password (12+ characters): ")
            if not 12 <= len(password) <= 256 or password != getpass.getpass("Confirm password: "):
                parser.error("Password is too short, too long, or confirmation differs")
            tenant = Tenant(name=args.tenant)
            user = User(email=email, password_hash=passwords.hash(password))
            db.add_all([tenant, user])
            db.flush()
            db.add(TenantMember(tenant_id=tenant.id, user_id=user.id, role="admin"))
            db.commit()
            print("Administrator created.")
        else:
            if not args.input.is_finite() or not args.output.is_finite() or min(args.input, args.output) < 0:
                parser.error("Prices must be finite and nonnegative")
            db.add(
                ModelPricing(
                    provider=args.provider,
                    model=args.model,
                    input_price_per_million=args.input,
                    output_price_per_million=args.output,
                )
            )
            db.commit()
            print("Pricing version created (USD per million tokens).")


if __name__ == "__main__":
    main()

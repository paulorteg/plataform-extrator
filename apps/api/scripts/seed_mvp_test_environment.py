from app.db.session import SessionLocal
from app.seeds.mvp_test_environment import config_from_env, seed_mvp_test_environment


def main() -> None:
    config = config_from_env()
    with SessionLocal() as session:
        result = seed_mvp_test_environment(session, config)

    print("MVP test environment seed completed")
    print(f"organization_id={result.organization_id}")
    print(f"user_id={result.user_id}")
    print(f"user_organization_id={result.user_organization_id}")
    print(f"role_key={result.role_key}")
    print(f"plan_id={result.plan_id}")
    print(f"package_id={result.package_id}")
    print(f"subscription_id={result.subscription_id}")
    print(f"organization_package_id={result.organization_package_id}")


if __name__ == "__main__":
    main()

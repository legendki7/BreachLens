import asyncio

from app.db.session import AsyncSessionFactory, engine
from app.reference_data.repository import SqlAlchemyReferenceDataRepository
from app.reference_data.seeder import seed_reference_data


async def main() -> None:
    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                summary = await seed_reference_data(
                    SqlAlchemyReferenceDataRepository(session)
                )
    finally:
        await engine.dispose()

    print(
        "Seeded reference data: "
        f"{summary.security_risks} risks, "
        f"{summary.scenarios} scenarios, "
        f"{summary.attack_patterns} attack patterns, "
        f"{summary.policy_profiles} policy profiles."
    )


if __name__ == "__main__":
    asyncio.run(main())

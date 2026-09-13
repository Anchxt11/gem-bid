import asyncio

from backend.app.pipeline.verification.base import OllamaLLMReconciler


async def main():
    reconciler = OllamaLLMReconciler()

    test_cases = [
        ("ACME PVT LTD", "ACME PRIVATE LIMITED"),
        ("SUNRISE TRADERS", "SUNRISE TRADING CO"),
        ("SHARMA ENGINEERING WORKS", "SHARMA ENGG WORKS PVT LTD"),
    ]

    for bidder_name, portal_name in test_cases:
        print(f"\nComparing: '{bidder_name}'  vs  '{portal_name}'")
        match_status, reason = await reconciler.reconcile_ambiguous_name(
            bidder_name, portal_name, context={"requirement": "manual test"}
        )
        print(f"  -> match_status: {match_status.value}")
        print(f"  -> reason: {reason}")


if __name__ == "__main__":
    asyncio.run(main())
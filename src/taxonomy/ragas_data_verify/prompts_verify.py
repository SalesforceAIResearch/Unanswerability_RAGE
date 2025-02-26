from ragas.llms.prompt import Prompt

verify_question_prompt = Prompt(
    name="verify_question",
    instruction="Verify whether the given question that can be fully answered from given context. Output 'answerable' as '1' if question can be fully answered from the given context, '-1' if answer is not present in the context. You will also check whether the answer is correct. Output 'correctness' as '1' if answer is correct based on the given context, '-1' if answer is not correct. You will also verify whether this question is useful for a customer or user. Output 'usefulness' as '1' if question can be useful for the customers or users, '-1' if answer is not useful at all.",
    examples=[
        {
            "context": "## Merchandise Info for Basin which is located at Marketplace\nMerchandise Info for Basin which is located at Marketplace\nBasin sells the following types of merchandise:\n- Beauty & Health\n- Gifts & Housewares\n- Health & Beauty",
            "question": "What types of merchandise does Basin sell?",
            "answer": "Basin sells the following types of merchandise:\n- Beauty & Health\n- Gifts & Housewares\n- Health & Beauty",
            "output": {
                    "answerable": "1",
                    "correctness": "1",
                    "usefulness": "1",
                    },
        },
        {
            "context": "# Annual Products for Walt Disney World Resorts Annual Products for Walt Disney World Resorts ## Basic Plan Package Basic Plan Package: The Basic Plan package is a great option for Guests who already have Theme Park Tickets but would like to add other package components to their reservation. While Basic Plan packages do not include Theme Park Tickets or the Dining Plan, they still offer all the convenience and value of a Walt Disney Travel Company package. They also offer Guests the convenience of being able to make payments online. Basic Plan packages can only be booked through Disney Central. The 2025 Basic Plan Package includes: Accommodations at a Walt Disney World® Resort hotel for 1-14 nights Magical Extras, including: Four miniature golf admission vouchers per package Four ESPN Wide World of Sports Complex admission vouchers per package Discounts and offerings on dining, entertainment, shopping, and more! Click here for a full list of updated locations. One souvenir luggage tag per person One additional admission to either miniature golf or ESPN Wide World of Sports Complex per person ## Ticketless Packages Ticketless Packages: Offer Dates: Booking Dates: February 27, 2024 - October 31, 2025 Travel Dates: January 1 - October 31, 2025",
            "question": "How many miniature golf admission vouchers do I have if I buy the 2025 Basic Plan Package?",
            "answer": "If you buy the 2025 Basic Plan Package, you will have four miniature golf admission vouchers per package. Additionally, each person in your party will receive two additional admission to miniature golf.",
            "output": {
                "answerable": "1",
                "correctness": "-1",
                "usefulness": "1",
            },
        },
        {
            "context": "# Annual Products for Walt Disney World Resorts Annual Products for Walt Disney World Resorts ## Basic Plan Package Basic Plan Package: The Basic Plan package is a great option for Guests who already have Theme Park Tickets but would like to add other package components to their reservation. While Basic Plan packages do not include Theme Park Tickets or the Dining Plan, they still offer all the convenience and value of a Walt Disney Travel Company package. They also offer Guests the convenience of being able to make payments online. Basic Plan packages can only be booked through Disney Central. The 2025 Basic Plan Package includes: Accommodations at a Walt Disney World® Resort hotel for 1-14 nights Magical Extras, including: Four miniature golf admission vouchers per package Four ESPN Wide World of Sports Complex admission vouchers per package Discounts and offerings on dining, entertainment, shopping, and more! Click here for a full list of updated locations. One souvenir luggage tag per person One additional admission to either miniature golf or ESPN Wide World of Sports Complex per person ## Ticketless Packages Ticketless Packages: Offer Dates: Booking Dates: February 27, 2024 - October 31, 2025 Travel Dates: January 1 - October 31, 2025",
            "question": "where to click for a full list of updated locations?",
            "answer": "The context provided includes the instruction to `Click here for a full list of updated locations,` but it does not provide an actual clickable link or a specific URL. Therefore, based on the given context, there is no way to directly click or access a full list of updated locations. For more detailed information, you would need to visit the official Walt Disney World Resorts website or contact Disney Central directly.",
            "output": {
                "answerable": "-1",
                "correctness": "1",
                "usefulness": "-1",
            },
        },
    ],
    input_keys=["context", "question", "answer"],
    output_key="output",
    output_type="json",
)

# disney_question_useful_prompt = Prompt(
#     name="question_useful_verification",
#     instruction="""If you are a customer of Disney, will you ask the following question? Output verdict as '1' if question is reasonable for a customer to ask, '-1' if answer is not reasonable.""",
#     examples=[
#         {
#             "question": "What types of merchandise does Basin sell?",
#             "output": {
#                 "reason": "The customer is likely to ask about types of merchandise sold in Basin.",
#                 "verdict": "1",
#             },
#         },
#         {
#             "question": "",
#             "output": {
#                 "reason": "The answer covers all the information in the ground_truth.",
#                 "verdict": "1",
#             },
#         }
#     ],
#     input_keys=["answer", "ground_truth"],
#     output_key="output",
#     output_type="json",
#     language="english",
# )
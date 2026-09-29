"""Development seed data.

Creates demo support users and sample complaints for local development.
This data is clearly separated from real CFPB data and real customer data.
"""

import json
import logging
from backend.models import db, SupportUser, Complaint, Customer, Classification, \
    PriorityDecision, StatusHistory, InternalNote, Assignment, Notification
from backend.auth import hash_password
from backend.utils.reference_generator import generate_reference
from backend.services.priority_engine import get_priority_engine
from backend.services.classifier import get_classifier

logger = logging.getLogger(__name__)

# Demo complaint descriptions (fictional, not from real customer data)
DEMO_COMPLAINTS = [
    {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "description": "I noticed an unauthorized charge of $450.00 on my credit card statement from a company I've never heard of. I need this investigated immediately. The transaction appeared on September 15th and I did not authorize it.",
    },
    {
        "name": "Robert Johnson",
        "email": "robert.j@example.com",
        "description": "Someone has accessed my checking account and made several withdrawals totaling $2,300. I don't recognize these transactions and I'm worried about identity theft. This is an emergency and I need help right now.",
    },
    {
        "name": "Maria Garcia",
        "email": "maria.g@example.com",
        "description": "My mortgage company applied a late fee to my account even though I paid on time. I have the confirmation number from my bank showing the payment was sent three days before the due date. I've called twice but no one has resolved this.",
    },
    {
        "name": "David Wilson",
        "email": "david.w@example.com",
        "description": "How do I check my credit score? I'm interested in getting a copy of my credit report but I'm not sure which bureau to contact. No rush on this, just whenever you have time.",
    },
    {
        "name": "Sarah Brown",
        "email": "sarah.b@example.com",
        "description": "I've been receiving threatening phone calls from a debt collection agency about a debt that isn't mine. They call multiple times a day and have used aggressive language. I've told them they have the wrong person but they continue to harass me.",
    },
    {
        "name": "Michael Lee",
        "email": "michael.l@example.com",
        "description": "My student loan servicer changed my repayment plan without notifying me. My monthly payment went from $350 to $580 and I cannot afford this. I'm struggling to make the payments and worried about defaulting.",
    },
    {
        "name": "Emily Davis",
        "email": "emily.d@example.com",
        "description": "I believe someone opened a credit card in my name. There's an account on my credit report that I never opened. This appears to be identity theft and I need this fraudulent account removed immediately.",
    },
    {
        "name": "James Taylor",
        "email": "james.t@example.com",
        "description": "I'm having trouble with my car loan. I missed one payment and now they're threatening repossession even though I've made all other payments on time for two years. I need help understanding my options.",
    },
    {
        "name": "Lisa Anderson",
        "email": "lisa.a@example.com",
        "description": "I tried to transfer $500 through a money transfer service and the funds never arrived at the destination. It's been over two weeks and the company keeps saying they're investigating but won't give me a refund.",
    },
    {
        "name": "Thomas Martinez",
        "email": "thomas.m@example.com",
        "description": "What is the process for disputing an error on my credit report? I just noticed something that looks incorrect. Can you tell me the steps I need to follow? General question about the dispute process.",
    },
    {
        "name": "Jennifer White",
        "email": "jennifer.w@example.com",
        "description": "I was charged a $35 overdraft fee on my checking account even though I had sufficient funds. My direct deposit came in the morning but the bank processed a charge from the night before first. This has happened three times this month totaling $105 in fees.",
    },
    {
        "name": "Christopher Harris",
        "email": "chris.h@example.com",
        "description": "My credit score dropped 120 points after a company incorrectly reported a debt as delinquent. I paid this account in full six months ago and have the receipt. This is urgent as I'm trying to get a mortgage and this is destroying my application.",
    },
]


def create_demo_users(config):
    """Create demo support staff accounts."""
    demo_users = [
        {
            "username": "admin",
            "email": "admin@complaint-system.dev",
            "password": config.get("DEMO_ADMIN_PASSWORD", "admin123dev"),
            "role": "admin",
            "display_name": "System Administrator",
        },
        {
            "username": "manager",
            "email": "manager@complaint-system.dev",
            "password": config.get("DEMO_MANAGER_PASSWORD", "manager123dev"),
            "role": "manager",
            "display_name": "Sarah Manager",
        },
        {
            "username": "agent1",
            "email": "agent1@complaint-system.dev",
            "password": config.get("DEMO_AGENT_PASSWORD", "agent123dev"),
            "role": "agent",
            "display_name": "Alex Agent",
        },
        {
            "username": "agent2",
            "email": "agent2@complaint-system.dev",
            "password": config.get("DEMO_AGENT_PASSWORD", "agent123dev"),
            "role": "agent",
            "display_name": "Jordan Agent",
        },
    ]

    created = []
    for user_data in demo_users:
        existing = SupportUser.query.filter_by(username=user_data["username"]).first()
        if not existing:
            user = SupportUser(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                display_name=user_data["display_name"],
            )
            db.session.add(user)
            created.append(user_data["username"])

    db.session.commit()
    if created:
        logger.info("Created demo users: %s", ", ".join(created))
    return created


def create_demo_complaints(config):
    """Create demo complaints with classification and prioritization."""
    if Complaint.query.count() > 0:
        logger.info("Demo complaints already exist, skipping.")
        return []

    classifier = get_classifier(config)
    engine = get_priority_engine()

    # Get agents for assignment
    agents = SupportUser.query.filter_by(role="agent", is_active=True).all()
    manager = SupportUser.query.filter_by(role="manager").first()

    created_refs = []
    for i, demo in enumerate(DEMO_COMPLAINTS):
        # Find or create customer
        customer = Customer.query.filter_by(email=demo["email"]).first()
        if not customer:
            customer = Customer(name=demo["name"], email=demo["email"])
            db.session.add(customer)
            db.session.flush()

        reference = generate_reference()

        # Classify
        classification = classifier.classify(demo["description"])

        # Calculate priority
        priority_result = engine.calculate_priority(
            text=demo["description"],
            category=classification["category"],
            subcategory=classification["subcategory"],
            confidence=classification["confidence"],
        )

        threshold = float(config.get("CONFIDENCE_THRESHOLD", 0.60))

        # Load team mapping
        try:
            import os
            categories_path = config.get("CATEGORIES_PATH", "config/categories.json")
            if os.path.exists(categories_path):
                with open(categories_path, "r") as f:
                    cat_config = json.load(f)
                team_mapping = cat_config.get("category_team_mapping", {})
                assigned_team = team_mapping.get(classification["category"], "General Support")
            else:
                assigned_team = "General Support"
        except Exception:
            assigned_team = "General Support"

        # Assign some complaints to agents
        assigned_to = None
        if agents and i < len(agents) * 3:
            assigned_to = agents[i % len(agents)].id

        # Vary statuses for demo
        statuses = ["submitted", "under_review", "in_progress", "submitted",
                     "under_review", "in_progress", "submitted", "waiting_for_customer",
                     "resolved", "submitted", "in_progress", "under_review"]
        status = statuses[i % len(statuses)]

        complaint = Complaint(
            reference=reference,
            customer_id=customer.id,
            customer_name=demo["name"],
            customer_email=demo["email"],
            description=demo["description"],
            system_category=classification["category"],
            system_subcategory=classification["subcategory"],
            system_confidence=classification["confidence"],
            model_version=classification["model_version"],
            current_category=classification["category"],
            current_subcategory=classification["subcategory"],
            system_priority=priority_result["priority"],
            current_priority=priority_result["priority"],
            priority_explanation=priority_result["explanation"],
            priority_signals=priority_result["signals"],
            needs_human_review=classification["confidence"] < threshold,
            status=status,
            assigned_team=assigned_team,
            assigned_to=assigned_to,
        )
        db.session.add(complaint)
        db.session.flush()

        # Record classification
        cls_record = Classification(
            complaint_id=complaint.id,
            category=classification["category"],
            subcategory=classification["subcategory"],
            confidence=classification["confidence"],
            model_version=classification["model_version"],
        )
        db.session.add(cls_record)

        # Record priority
        pri_record = PriorityDecision(
            complaint_id=complaint.id,
            priority=priority_result["priority"],
            score=priority_result["score"],
            explanation=priority_result["explanation"],
            signals=priority_result["signals"],
        )
        db.session.add(pri_record)

        # Record status history
        status_record = StatusHistory(
            complaint_id=complaint.id,
            old_status=None,
            new_status="submitted",
            changed_by="system",
            changed_by_name="System",
            reason="Demo complaint created",
        )
        db.session.add(status_record)

        # Add extra status history for non-submitted complaints
        if status != "submitted":
            status_record2 = StatusHistory(
                complaint_id=complaint.id,
                old_status="submitted",
                new_status=status,
                changed_by=manager.id if manager else "system",
                changed_by_name=manager.display_name if manager else "System",
                reason="Demo status progression",
            )
            db.session.add(status_record2)

        # Add a demo note to some complaints
        if i % 3 == 0 and agents:
            note = InternalNote(
                complaint_id=complaint.id,
                author_id=agents[0].id,
                content="Initial review completed. Customer contacted for additional details.",
            )
            db.session.add(note)

        # Customer notification
        notification = Notification(
            complaint_id=complaint.id,
            customer_id=customer.id,
            message=f"Your complaint has been submitted successfully. Reference: {reference}",
            notification_type="status_update",
        )
        db.session.add(notification)

        created_refs.append(reference)

    db.session.commit()
    logger.info("Created %d demo complaints", len(created_refs))
    return created_refs


def seed_database(config):
    """Run all seed data creation."""
    logger.info("Seeding database with demo data...")
    create_demo_users(config)
    refs = create_demo_complaints(config)
    logger.info("Database seeded. Demo complaint references: %s",
                ", ".join(refs[:5]) + "..." if len(refs) > 5 else ", ".join(refs))
    return refs

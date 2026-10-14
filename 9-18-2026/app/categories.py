from enum import Enum


class Category(str, Enum):
    SOFTWARE = "Software"
    RESTAURANTS = "Restaurants"
    HOME_IMPROVEMENT = "Home Improvement"
    MARKETING_AGENCY = "Marketing Agency"
    EDUCATION = "Education"
    GROCERY_SUPERMARKETS = "Grocery & Supermarkets"
    RETAIL_ECOMMERCE = "Retail & E-commerce"
    HEALTHCARE_MEDICAL = "Healthcare & Medical"
    FITNESS_WELLNESS = "Fitness & Wellness"
    BEAUTY_PERSONAL_CARE = "Beauty & Personal Care"
    REAL_ESTATE = "Real Estate"
    CONSTRUCTION_CONTRACTING = "Construction & Contracting"
    AUTOMOTIVE = "Automotive"
    BANKING_LENDING = "Banking & Lending"
    INSURANCE = "Insurance"
    ACCOUNTING_TAX = "Accounting & Tax Services"
    LEGAL_SERVICES = "Legal Services"
    TRAVEL_HOSPITALITY = "Travel & Hospitality"
    ENTERTAINMENT_RECREATION = "Entertainment & Recreation"
    TRANSPORTATION_LOGISTICS = "Transportation & Logistics"
    MANUFACTURING_INDUSTRIAL = "Manufacturing & Industrial"
    AGRICULTURE_FARMING = "Agriculture & Farming"
    PET_CARE_SUPPLIES = "Pet Care & Supplies"
    STAFFING_RECRUITING = "Staffing & Recruiting"
    NONPROFITS_CHARITIES = "Nonprofits & Charities"
    OTHER = "Other"
    UNKNOWN = "Unknown / Insufficient Information"


CATEGORY_DEFINITIONS: dict[Category, str] = {
    Category.SOFTWARE: (
        "The primary product is software, including desktop or mobile apps, cloud "
        "platforms, developer tools, or software-as-a-service products."
    ),
    Category.RESTAURANTS: (
        "Prepares and sells meals or drinks for dine-in, takeout, or delivery, "
        "including restaurants, cafes, bars, bakeries, and food trucks."
    ),
    Category.HOME_IMPROVEMENT: (
        "Provides products or services used to repair, renovate, maintain, or improve "
        "homes, including plumbing, electrical, roofing, painting, landscaping, and hardware."
    ),
    Category.MARKETING_AGENCY: (
        "Helps organizations attract customers or promote brands through advertising, "
        "branding, content, public relations, social media, or SEO."
    ),
    Category.EDUCATION: (
        "Primarily teaches or trains people, including schools, universities, tutoring, "
        "online courses, and professional training."
    ),
    Category.GROCERY_SUPERMARKETS: (
        "Primarily sells groceries, beverages, household necessities, and other everyday supplies."
    ),
    Category.RETAIL_ECOMMERCE: (
        "Primarily sells physical consumer products through stores, websites, or marketplaces."
    ),
    Category.HEALTHCARE_MEDICAL: (
        "Provides medical care, diagnosis, treatment, rehabilitation, pharmacy, dental, "
        "or other clinical health services."
    ),
    Category.FITNESS_WELLNESS: (
        "Supports physical fitness, preventive wellness, or general well-being through "
        "gyms, studios, trainers, or wellness programs."
    ),
    Category.BEAUTY_PERSONAL_CARE: (
        "Provides appearance, grooming, cosmetic, spa, salon, barber, or personal-care services or products."
    ),
    Category.REAL_ESTATE: (
        "Primarily buys, sells, rents, develops, brokers, or manages residential or commercial property."
    ),
    Category.CONSTRUCTION_CONTRACTING: (
        "Builds, renovates, or performs major structural work on residential, commercial, "
        "or industrial property."
    ),
    Category.AUTOMOTIVE: (
        "Primarily sells, rents, maintains, repairs, details, or supplies parts for vehicles."
    ),
    Category.BANKING_LENDING: (
        "Provides banking, credit, mortgage, loan, payment, or financing services."
    ),
    Category.INSURANCE: (
        "Sells, underwrites, administers, or brokers insurance policies."
    ),
    Category.ACCOUNTING_TAX: (
        "Provides bookkeeping, accounting, auditing, payroll, tax preparation, or financial reporting."
    ),
    Category.LEGAL_SERVICES: (
        "Provides legal advice, representation, document preparation, mediation, or related law services."
    ),
    Category.TRAVEL_HOSPITALITY: (
        "Provides accommodations, travel planning, tours, reservations, or services for travelers."
    ),
    Category.ENTERTAINMENT_RECREATION: (
        "Primarily provides leisure, entertainment, attractions, gaming, cultural, or recreational activities."
    ),
    Category.TRANSPORTATION_LOGISTICS: (
        "Transports people or goods or manages shipping, freight, delivery, moving, or distribution."
    ),
    Category.MANUFACTURING_INDUSTRIAL: (
        "Manufactures physical goods or supplies machinery, equipment, materials, or industrial services."
    ),
    Category.AGRICULTURE_FARMING: (
        "Grows crops, raises animals, produces agricultural goods, or supplies farms."
    ),
    Category.PET_CARE_SUPPLIES: (
        "Provides veterinary care, grooming, boarding, training, or products for pets."
    ),
    Category.STAFFING_RECRUITING: (
        "Connects employers and workers through recruiting, staffing, employment, or executive-search services."
    ),
    Category.NONPROFITS_CHARITIES: (
        "Serves a public, social, religious, environmental, or charitable mission rather "
        "than distributing profits to owners."
    ),
    Category.OTHER: (
        "The organization is identifiable, but its primary activity does not fit another category."
    ),
    Category.UNKNOWN: (
        "Available evidence is insufficient or unreliable, or the organization cannot be identified."
    ),
}


def category_prompt() -> str:
    return "\n".join(
        f"- {category.value}: {definition}"
        for category, definition in CATEGORY_DEFINITIONS.items()
    )

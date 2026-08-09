from django.shortcuts import render

from calendar_app.views import upcoming_widget_items
from .models import Banner, TopHeader, NewsPopup


HOME_SECTIONS = [
    {
        "id": "who-we-are",
        "eyebrow": "Who We Are",
        "title": "Temple life rooted in service, study, and devotion",
        "lead": "Explore the temple story, philosophy, and daily rhythm through the linked pages below.",
        "image": "themes/images/GNgkp.jpg",
        "image_alt": "ISKCON Gorakhpur temple exterior",
        "cta": {
            "label": "Open About Us",
            "href": "/who-we-are/about-us",
        },
        "items": [
            {
                "id": "about-us",
                "title": "About Us",
                "text": "A short introduction to the temple and its mission.",
                "href": "/who-we-are/about-us",
                "button_label": "Read more",
            },
            {
                "id": "mission",
                "title": "Mission",
                "text": "The temple's service priorities and preaching goals.",
                "href": "/who-we-are/our-mission",
                "button_label": "Read more",
            },
            {
                "id": "founder",
                "title": "Founder",
                "text": "Srila Prabhupada's vision and ISKCON's legacy.",
                "href": "/who-we-are/founder-acharya",
                "button_label": "Read more",
            },
            {
                "id": "history",
                "title": "History",
                "text": "How the temple and its community developed over time.",
                "href": "/who-we-are/our-history",
                "button_label": "Read more",
            },
            {
                "id": "philosophy",
                "title": "Philosophy",
                "text": "The spiritual principles that guide temple life.",
                "href": "/who-we-are/our-philosophy",
                "button_label": "Read more",
            },
            {
                "id": "schedule",
                "title": "Schedule",
                "text": "Daily arati, darshan, and temple timing details.",
                "href": "/who-we-are/temple-schedule",
                "button_label": "Read more",
            },
            {
                "id": "resources",
                "title": "Resources",
                "text": "Study materials, books, and devotional references.",
                "href": "/who-we-are/resources",
                "button_label": "Read more",
            },
        ],
    },
    {
        "id": "activities",
        "eyebrow": "Activities",
        "title": "Programs that build bhakti through practice",
        "lead": "These cards open the existing activity pages, while the section itself stays on the homepage for quick access.",
        "image": "themes/images/Life-Membership.jpg",
        "image_alt": "Life membership program",
        "cta": {
            "label": "Join Life Membership",
            "href": "/services/life-membership",
        },
        "alt": True,
        "items": [
            {
                "id": "life-membership",
                "title": "Life Membership",
                "text": "Become part of the ISKCON family and support temple service.",
                "href": "/services/life-membership",
                "button_label": "Open page",
            },
            {
                "id": "shiksha",
                "title": "Shiksha",
                "text": "Structured bhakti steps for steady spiritual growth.",
                "href": "/services/shiksha",
                "button_label": "Open page",
            },
            {
                "id": "harinam",
                "title": "Harinam",
                "text": "Public chanting and congregational sankirtan.",
                "href": "/services/harinam-sankirtana",
                "button_label": "Open page",
            },
            {
                "id": "sunday-feast",
                "title": "Sunday Feast",
                "text": "Weekly devotional gathering with kirtan and prasadam.",
                "href": "/services/sunday-feast",
                "button_label": "Open page",
            },
            {
                "id": "food-for-life",
                "title": "Food for Life",
                "text": "Prasadam distribution and community seva.",
                "href": "https://www.foodforlifes.in/",
                "target": "_blank",
                "rel": "noopener noreferrer",
                "button_label": "Visit site",
            },
        ],
    },
    {
        "id": "festivals",
        "eyebrow": "Festivals",
        "title": "Seasonal observances, celebrations, and temple events",
        "lead": "Use these links to open the Vaishnava calendar and festival views for deeper details.",
        "image": "themes/images/nagar_kirtan.jpg",
        "image_alt": "Devotional festival procession",
        "cta": {
            "label": "View calendar",
            "href": "/calendar/",
        },
        "items": [
            {
                "id": "calendar",
                "title": "Calendar",
                "text": "See the Vaishnava calendar and yearly observances.",
                "href": "/calendar/",
                "button_label": "Read more",
            },
            {
                "id": "festival-list",
                "title": "Festivals",
                "text": "Read the festival feed and featured celebrations.",
                "href": "/calendar/festivals/",
                "button_label": "Read more",
            },
            {
                "id": "ekadashi",
                "title": "Ekadashi",
                "text": "Browse fasting days and Ekadashi updates.",
                "href": "/calendar/ekadashi/",
                "button_label": "Read more",
            },
            {
                "id": "appearance",
                "title": "Appearance",
                "text": "Appearance days of the Lord and acharyas.",
                "href": "/calendar/appearance-days/",
                "button_label": "Read more",
            },
            {
                "id": "disappearance",
                "title": "Disappearance",
                "text": "Commemoration of departure days of great souls.",
                "href": "/calendar/disappearance-days/",
                "button_label": "Read more",
            },
            {
                "id": "events",
                "title": "Events",
                "text": "Special programs and congregation gatherings.",
                "href": "/events/",
                "button_label": "Read more",
            },
        ],
    },
    {
        "id": "donate",
        "eyebrow": "Donate",
        "title": "Seva opportunities that support temple life",
        "lead": "Each donation card opens the existing payment flow or donation page. The homepage only adds anchor navigation.",
        "image": "themes/images/Shastra-Daan.jpg",
        "image_alt": "Shastra Daan seva",
        "cta": {
            "label": "Start with Shastra Daan",
            "href": "/donations/shastra-daan",
        },
        "alt": True,
        "items": [
            {
                "id": "shastra-daan",
                "title": "Shastra Daan",
                "text": "Sponsor Bhagavad-gita distribution and book seva.",
                "href": "/donations/shastra-daan",
                "button_label": "Donate now",
            },
            {
                "id": "temple-seva",
                "title": "Temple Seva",
                "text": "Support deity worship, maintenance, and temple operations.",
                "href": "/donations/temple-seva",
                "button_label": "Donate now",
            },
            {
                "id": "annadana",
                "title": "Annadana",
                "text": "Sponsor prasadam distribution to the needy.",
                "href": "/donations/annadana-seva",
                "button_label": "Donate now",
            },
            {
                "id": "nitya-seva",
                "title": "Nitya Seva",
                "text": "Recurring seva that supports ongoing temple service.",
                "href": "/donations/nitya-seva",
                "button_label": "Donate now",
            },
            {
                "id": "janmashtami",
                "title": "Janmashtami",
                "text": "Support the Lord's appearance festival and celebrations.",
                "href": "/donations/janmashtami-seva",
                "button_label": "Donate now",
            },
            {
                "id": "tula-daan",
                "title": "Tula Daan",
                "text": "Offer seva through the weighing ceremony donation.",
                "href": "/donations/tula-daan-utsav",
                "button_label": "Donate now",
            },
        ],
    },
]


def home_view(request):
    banners = Banner.objects.all().order_by('-id')
    top_headers = TopHeader.objects.all().order_by('-id')
    news_popup = NewsPopup.objects.filter(active=True).order_by('-id').first()
    context = {
        "banner": banners,
        "top_header": top_headers,
        "news_popup": news_popup,
        "home_sections": HOME_SECTIONS,
        "upcoming_widget_items": upcoming_widget_items(),
    }
    return render(request, 'home.html', context)

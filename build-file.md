Feature Implementation Request: Authentication & RBAC

I am working on a machine learning-powered recommendation platform built with FastAPI. The application is located at:

\\wsl.localhost\Ubuntu\home\techyz-admin\sevenwings\02_startups\neuro-adaptive-recommender\fastapi_app
I want to enhance the platform by introducing a proper authentication, authorization, and subscription management system.

For now, let's focus exclusively on Authentication and RBAC (Role-Based Access Control).

Context

The system serves two primary user groups:

Clinicians
Parents

For now only, there are no specific endpoints that should be closed as they needed by both roles (no need for permission restrictions)

Objectives

Please review the existing FastAPI codebase and design a production-ready authentication system that integrates cleanly with the current architecture.

Authentication Requirements
Implement user registration and login.
Implement secure password hashing.
Implement JWT-based authentication (access and refresh tokens).
Implement protected API routes.
Implement token refresh and logout mechanisms.
Implement proper error handling and security best practices.
Support role information within authentication tokens.
RBAC Requirements


Separation of concerns (routers, services, repositories, auth modules)
Future Roadmap (Do Not Implement Yet)
You build the auth models here: \\wsl.localhost\Ubuntu\home\techyz-admin\sevenwings\02_startups\neuro-adaptive-recommender\fastapi_app\models\auth_models.py

ANd it schemas here: 
\\wsl.localhost\Ubuntu\home\techyz-admin\sevenwings\02_startups\neuro-adaptive-recommender\fastapi_app\schema\

create a folder to keep the routers, and move the routers.py(rename it as recommend-router.py) inside of the router folder()

After authentication is complete, we will implement:

Subscription plans
Payment integration
Feature gating based on subscription tiers
Trial accounts
Usage quotas and limits

For now, focus only on designing and implementing a robust Authentication and RBAC foundation that can support these future subscription features.

Before making changes, provide a brief assessment of the current architecture, identify any authentication-related gaps, and explain the implementation approach.
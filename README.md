# AirAssist

EU 261/2004 flight-compensation claim-management web app.

Development email behavior:
When you run the Django dev server with `airassist.settings.dev`, account emails are written to the server console by default via Django's console email backend. After creating a case locally, check the backend terminal to see the temporary password.

Optional overrides:
- `DJANGO_EMAIL_BACKEND` to switch the dev email backend.
- `DJANGO_DEFAULT_FROM_EMAIL` to change the sender address.

Setup instructions and architecture notes will be added in Task 16.

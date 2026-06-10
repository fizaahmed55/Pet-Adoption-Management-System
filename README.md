# Fur Ever Paws - Pet Adoption Management System

Fur Ever Paws is a database-driven desktop application for managing the complete pet adoption workflow. The system is built with **Python**, **CustomTkinter**, and **Oracle Database**. It supports role-based access for Admin, Adopter, Shelter Staff, and Veterinarian users.

The system manages pets, shelters, adopters, applications, staff document verification, home checks, veterinarian medical/vaccination records, final adoption, payment, donation, feedback, and reports.

---

## 1. Project Objective

The objective of this project is to replace manual pet adoption record keeping with a structured database management system. The system ensures that adoption is completed only after proper adopter verification, home check, pet medical clearance, vaccination record, admin approval, and payment finalization.

---

## 2. Main Features

### Adopter Features

* Register as a new adopter.
* Login using email and password.
* View pet gallery.
* Open full pet profile.
* View pet details, breed, category, behavior, health, vaccination, and expected lifetime.
* Apply for available pets.
* View own applications.
* View own completed adoptions.
* Submit feedback after successful adoption.

### Shelter Staff Features

* View shelter dashboard.
* Add new pets.
* Update pet details.
* Update pet availability and health status.
* Add pet images.
* Delete pets if no adoption history is connected.
* View applications related to shelter pets.
* Create and verify application documents.
* Add home check records.
* Recommend or approve applications after verification.

### Veterinarian Features

* View pet health details.
* Add medical records.
* Update medical records.
* Delete incorrect medical records.
* Add vaccination records.
* Update vaccination records.
* Delete incorrect vaccination records.
* Mark pet as healthy or under treatment.

### Admin Features

* View complete system dashboard.
* Manage users.
* Manage shelters.
* View all pets and applications.
* Check final adoption requirements.
* Finalize adoption.
* Record payment.
* View donations.
* View feedback.
* View system reports.

---

## 3. Technologies Used

| Component              | Technology           |
| ---------------------- | -------------------- |
| Programming Language   | Python               |
| GUI Framework          | CustomTkinter        |
| Database               | Oracle Database      |
| Database Tool          | Oracle SQL Developer |
| Python Database Driver | oracledb             |
| Image Processing       | Pillow               |
| IDE                    | Visual Studio Code   |

---

## 4. Database Overview

The system uses an Oracle database schema named **PAMS**. The database is normalized and uses primary keys, foreign keys, constraints, views, indexes, and PL/SQL packages.

### Main Tables

* `ROLE`
* `USER_ACCOUNT`
* `ADOPTER`
* `SHELTER`
* `SHELTER_STAFF`
* `VETERINARIAN`
* `PET_CATEGORY`
* `BREED`
* `PET`
* `PET_IMAGE`
* `ADOPTION_APPLICATION`
* `APPLICATION_DOCUMENT`
* `HOME_CHECK`
* `MEDICAL_RECORD`
* `VACCINATION_RECORD`
* `ADOPTION_RECORD`
* `PAYMENT`
* `DONOR`
* `DONATION`
* `REVIEW_FEEDBACK`

### Main Views

* `VW_AVAILABLE_PETS`
* `VW_ADOPTION_PIPELINE`
* `VW_PET_HEALTH_SUMMARY`

### Main PL/SQL Package

* `PKG_ADOPTION`

The package contains procedures for adoption operations:

* `approve_application`
* `reject_application`
* `finalize_adoption`

---

## 5. Role-Based Workflow

The adoption workflow follows this sequence:

1. Adopter registers an account.
2. Adopter logs in.
3. Adopter views the pet gallery.
4. Adopter opens the full pet profile.
5. Adopter submits an adoption application.
6. Shelter staff reviews the application.
7. Shelter staff creates and verifies the application document.
8. Shelter staff performs the home check.
9. Shelter staff approves or recommends the application.
10. Veterinarian adds medical and vaccination records.
11. Admin checks all final adoption requirements.
12. Admin finalizes adoption.
13. Payment is recorded.
14. Pet status becomes Adopted.
15. Adopter can submit feedback.

---

## 6. How to Run the Application

Install required packages:

```bash
pip install customtkinter oracledb pillow
```

Use this Oracle connection:

```text
Username: pams
Password: pams
Service Name: ORCLPDB
Host: localhost
Port: 1521
```

Python database settings:

```python
DB_USER = "pams"
DB_PASSWORD = "pams"
DB_DSN = "localhost:1521/ORCLPDB"
```

Run the application:

```powershell
python -m py_compile app/main.py
python app/main.py
```

---

## 7. Demo Login Accounts

| Role          | Email                                       | Password   |
| ------------- | ------------------------------------------- | ---------- |
| Admin         | [admin@pams.com](mailto:admin@pams.com)     | admin123   |
| Shelter Staff | [staff@pams.com](mailto:staff@pams.com)     | staff123   |
| Veterinarian  | [vet@pams.com](mailto:vet@pams.com)         | vet123     |
| Adopter       | [adopter@pams.com](mailto:adopter@pams.com) | adopter123 |

---


## 8. Conclusion

Fur Ever Paws is a complete database management system for pet adoption. It uses a proper Oracle relational database with normalized tables, constraints, views, indexes, and PL/SQL procedures. The system separates the responsibilities of adopters, shelter staff, veterinarians, and admin users. It ensures that adoption is finalized only after document verification, home check, pet medical clearance, vaccination record, admin approval, and payment completion.

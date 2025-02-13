# echo - Django E-Commerce Platform

## Project Overview
This is a Django-based e-commerce platform for selling headphones. The platform allows users to browse and purchase headphones with different connectivity types, colors, and price variations.

## Features
- User authentication and profile management
- Product catalog with filtering and search options
- Product variants with different prices and stock levels
- Secure payment integration
- Order management system
- Cloud-based image storage using Cloudinary
- Admin dashboard for managing products, orders, and users

## Tech Stack
- **Backend:** Django
- **Database:** PostgreSQL (AWS RDS)
- **Storage:** Cloudinary (for image storage)
- **Hosting:** AWS EC2 instance

## Installation
### Prerequisites
Ensure you have the following installed:
- Python 3.x
- PostgreSQL
- pip (Python package manager)
- virtualenv (recommended for virtual environments)

### Steps to Set Up the Project
1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd <project_directory>
   ```
2. **Create and Activate Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set Up Environment Variables:**
   Create a `.env` file and add the required variables such as:
   ```env
    SECRET_KEY=<your_secret_key>
    DEBUG=<your_debug_value>
    DB_NAME=<your_db_name>
    DB_USER=<your_db_user>
    DB_PASSWORD=<your_db_password>
    DB_HOST=<your_db_host>
    DB_PORT=<your_db_port>
    
    CLOUDINARY_CLOUD_NAME=<your_cloudinary_cloud_name>
    CLOUDINARY_API_KEY=<your_cloudinary_api_key>
    CLOUDINARY_API_SECRET=<your_cloudinary_api_secret>
    
    EMAIL_HOST_USER=<your_email_host_user>
    EMAIL_HOST_PASSWORD=<your_email_host_password>
    
    GOOGLE_CLIENT_ID=<your_google_client_id>
    GOOGLE_CLIENT_SECRET=<your_google_client_secret>
    GOOGLE_CALLBACK_URL=<your_google_callback_url>
    
    RAZORPAY_KEY_ID=<your_razorpay_key_id>
    RAZORPAY_KEY_SECRET=<your_razorpay_key_secret>
   ```
5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```
6. **Create a Superuser (Admin Panel Access):**
   ```bash
   python manage.py createsuperuser
   ```
7. **Run the Development Server:**
   ```bash
   python manage.py runserver
   ```
8. **Access the Application:**
   - Frontend: `http://127.0.0.1:8000/`
   - Admin Panel: `http://127.0.0.1:8000/manager/login`

## Deployment
1. **Set Up EC2 Instance:**
   - Install dependencies (`pip install -r requirements.txt`)
   - Set up PostgreSQL on AWS RDS
   - Configure Gunicorn and Nginx (or alternative HTTP server)

2. **Collect Static Files:**
   ```bash
   python manage.py collectstatic
   ```
3. **Restart Gunicorn and Nginx:**
   ```bash
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```
## Contact
For any inquiries, feel free to reach out to Ajmal Mohammed via email or LinkedIn.


# Banking-App-Project
Authors: Daniel Escalona, Samuel Pike, Lorena Basulto

## Description

Our project is a banking web application where registered users have the option of creating bank accounts and making transactions between their accounts and with other users. The types of transaction include deposit, withdrawal, and transfer.

## Core Functionality
* Register as a new user with email and password
* Create multiple bank accounts for one user and display them on the website
* Deposit/withdraw money from one account
* Transfer money between accounts (it could be between multiple accounts owned by the same user or accounts owned by different users)
* View transaction history (also includes transfers received and sent)
* Register/Login page, login is required for users to see any information
* Passwords will be encrypted using a hashing function
* Top navigation bar that includes multiple links to different pages in the website

## Technologies
* PostgreSQL
* Flask Framework (Python web dev framework)
* Flask-bcrypt for password hashing, https://flask-bcrypt.readthedocs.io/en/1.0.1/
* Flask-psycopg2 library to manage postgres database
* Bootstrap CSS Framework

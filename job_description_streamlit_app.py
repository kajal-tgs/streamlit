import streamlit as st
import requests

USERNAME = st.secrets["my_app_credentials"]["username"]
PASSWORD = st.secrets["my_app_credentials"]["password"]

# Streamlit UI elements
logo = st.image('company_bench.png', width=300)  # Adjust the width as needed
st.title("Job Description Analyzer")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # Check if login credentials are correct
    if st.button("Login"):
        if username == USERNAME and password == PASSWORD:
            # Authentication successful, set the authenticated state to True
            st.session_state.authenticated = True
        else:
            # Authentication failed
            st.warning("Incorrect username or password")

if st.session_state.authenticated:
    # Replace the login section with the upload file section
    st.empty()  # Clear the login section

    # Input area for job description
    job_description = st.text_area("Enter Job Description")

    # Dropdown for selecting role
    roles = ["Java Backend Developer","Spring Framework Developer","Java Microservices Developer","Java API Developer","Java DevOps Engineer","Python Backend Developer","Django Developer","Flask Developer","Python API Developer","Python Data Engineer","Node.js Backend Developer","Express.js Developer","Node.js API Developer","Node.js Microservices Developer","Node.js DevOps Engineer","Ruby Backend Developer","Ruby on Rails Developer","Ruby API Developer","Ruby Microservices Developer","Ruby DevOps Engineer","PHP Backend Developer","Laravel Developer","Symfony Developer","PHP API Developer","PHP DevOps Engineer","C# Backend Developer","ASP.NET Developer",".NET Core Developer","C# API Developer","C# Microservices Developer","Go Backend Developer","Go Microservices Developer","Go API Developer","Go DevOps Engineer","Go Cloud Engineer","Scala Backend Developer","Akka Developer","Play Framework Developer","Scala API Developer","Scala Microservices Developer","Rust Backend Developer","Rust API Developer","Rust Systems Developer","Rust Network Developer","Rust Blockchain Developer","Kotlin Backend Developer","Spring Boot Developer (Kotlin)","Ktor Developer","Kotlin API Developer","Kotlin Microservices Developer","JavaScript Frontend Developer","React.js Developer","Angular Developer","Vue.js Developer","Ember.js Developer","TypeScript Frontend Developer","React.js Developer (TypeScript)","Angular Developer (TypeScript)","Vue.js Developer (TypeScript)","Ember.js Developer (TypeScript)","HTML/CSS Frontend Developer","UI/UX Designer","Frontend Web Designer","HTML Email Developer","Responsive Web Designer","WebAssembly Frontend Developer","Rust Web Developer (WebAssembly)","C++ Web Developer (WebAssembly)","AssemblyScript Developer","WebAssembly Graphics Developer","Frontend Framework Developer","Material-UI Developer","Bootstrap Developer","Foundation Developer","Bulma Developer","Mobile Web Frontend Developer","Progressive Web App (PWA) Developer","AMP Developer (Accelerated Mobile Pages)","Mobile-First Web Developer","Hybrid App Developer","DevOps Engineer","Infrastructure Engineer","Site Reliability Engineer (SRE)","Cloud DevOps Engineer","Automation Engineer","Kubernetes Engineer","Docker Engineer","Containerization Specialist","DevOps Container Engineer","Container Orchestration Engineer","AWS DevOps Engineer","Azure DevOps Engineer","Google Cloud DevOps Engineer","Cloud Automation Specialist","Multi-Cloud DevOps Engineer","CI/CD Engineer","Build and Release Engineer","DevOps CI/CD Specialist","Jenkins Engineer","GitLab CI/CD Engineer","Configuration Management Engineer","Ansible Engineer","Puppet Engineer","Chef Engineer","SaltStack Engineer","DevOps Monitoring Engineer","Observability Engineer","Logging and Monitoring Specialist","Splunk Engineer","ELK Stack Engineer","DevSecOps Engineer","Security Automation Engineer","DevOps Security Specialist","Security Infrastructure Engineer","Secure Deployment Engineer","MEAN Stack Developer","MERN Stack Developer","Java Fullstack Developer","Python Fullstack Developer",".NET Fullstack Developer","Ruby on Rails Fullstack Developer","PHP Fullstack Developer","JavaScript Fullstack Developer","Angular Fullstack Developer","React Fullstack Developer","Salesforce Administrator","Salesforce Developer","Salesforce Consultant","Salesforce Architect","Salesforce Business Analyst","Salesforce Lightning Developer","Salesforce Integration Specialist","Salesforce Marketing Cloud Specialist","Salesforce CPQ Specialist","Salesforce Data Analyst","ServiceNow Developer","ServiceNow Administrator","ServiceNow Consultant","ServiceNow Architect","ServiceNow Implementation Specialist","ServiceNow ITOM Developer","ServiceNow ITSM Consultant","ServiceNow Integration Developer","ServiceNow Platform Developer","ServiceNow Technical Lead","AWS Cloud Architect","AWS Solutions Architect","AWS DevOps Engineer","AWS SysOps Administrator","AWS Developer","AWS Security Engineer","AWS Data Engineer","AWS Machine Learning Engineer","AWS Big Data Engineer","AWS Network Engineer","Azure Cloud Architect","Azure Solutions Architect","Azure DevOps Engineer","Azure Administrator","Azure Developer","Azure Security Engineer","Azure Data Engineer","Azure AI Engineer","Azure IoT Developer","Azure Networking Engineer","Machine Learning Engineer","Data Scientist","AI Research Scientist","Natural Language Processing (NLP) Engineer","Computer Vision Engineer","Deep Learning Engineer","Data Analyst (with ML specialization)","Algorithm Engineer","Machine Learning Operations (MLOps) Engineer","AI/ML Product Manager","Data Engineer","Data Warehouse Engineer","ETL Developer","Big Data Engineer","Cloud Data Engineer","Data Integration Engineer","Data Pipeline Engineer","Data Architect","Streaming Data Engineer","Database Engineer","SAP Consultant","SAP ABAP Developer","SAP Functional Analyst","SAP Basis Administrator","SAP Security Analyst","SAP Fiori Developer","SAP BI/BW Consultant","SAP HANA Developer","SAP SD Consultant","SAP MM Consultant"]  # Your role list here
    selected_role = st.selectbox("Select Role", roles)

    # Dropdown for selecting expertise level
    expertise_levels = ["Beginner", "Intermediate", "Advanced"]
    selected_expertise = st.selectbox("Select Expertise Level", expertise_levels)

    # Add a "Generate Questions" button
    if st.button("Generate Questions"):
        # Send the data to your Flask service for analysis
        payload = {
            "jobdescription": job_description,
            "role": selected_role,
            "expertiselevel": selected_expertise
        }
        response = requests.post("https://hbz5l8r4ob.execute-api.ap-south-1.amazonaws.com/prod/v1/joblisting/questions", json=payload)

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            questions_data = data.get("questions", [])

            if questions_data:
                st.write("Analized Result:")

                for index, question_data in enumerate(questions_data):
                    question = question_data.get("question", "")
                    answer = question_data.get("answer", "")
                    keywords = question_data.get("keywords", [])

                    # Append keywords to the question
                    question_with_keywords = f"Question {index + 1}: {question} (Keywords: {', '.join(keywords)})"

                    # Display only the answer when you expand a question
                    with st.expander(question_with_keywords):
                        st.write(f"Answer: {answer}")
            else:
                st.error("No questions found in the analysis result.")
        else:
            st.error("Error analyzing the job description.")

    # Add a "Reset" button next to the "Generate Questions" button
    if st.button("Reset"):
        st.session_state.pop("analysis_results", None)  # Clear the analysis results

    # Add the terms and conditions as a downloadable link
    terms_and_conditions = """
    ## Techila Global Services Terms and Conditions

    **Company Information:**
    Techila Global Services
    402, Summer Court
    Magarpatta City
    Hadapsar, Pune, Maharashtra 411028
    India

    **Type of Service/Product:**
    Techila Global Services provides consulting and technology services, specializing in Salesforce and cloud-based solutions.

    **User Registration:**
    To use Techila Global Services, users must create an account with a username, password, and email address, and agree to the terms and conditions of service.

    **Privacy Policy:**
    Techila Global Services takes user privacy seriously. Please review our Privacy Policy for more information on how we collect, use, and protect your personal data.

    **User Conduct:**
    Users agree to use the Techila Global Services website and services responsibly and ethically, without harming the website or interfering with other users' enjoyment.

    **Intellectual Property:**
    All intellectual property rights in the Techila Global Services website and services, including trademarks, copyrights, and patents, are owned by Techila Global Services. Users are granted a non-exclusive, non-transferable license for personal, non-commercial use.

    **Limitation of Liability:**
    Techila Global Services is not liable for any damages or losses incurred by users due to using the website or services, including indirect, incidental, special, or consequential damages.

    **Termination:**
    Techila Global Services may terminate or suspend a user's access to the website or services at any time, for any reason, without prior notice.

    **Governing Law and Jurisdiction:**
    These terms and conditions are governed by the laws of India, with disputes subject to the jurisdiction of the courts of Pune, India.

    **Contact Information:**
    If you have any questions or concerns about these terms and conditions, please contact us at [email protected]

    **Any Other Specific Clauses:**
    None.
    """

    # Create a downloadable link for terms and conditions
    st.markdown("**Download Terms and Conditions**")
    st.download_button(
        label="Download Terms and Conditions",
        data=terms_and_conditions,
        file_name="terms_and_conditions.txt",
        key="terms_and_conditions"
    )


from flask import Flask, json
from flask import jsonify
from flask import request
import requests

from langchain.llms import OpenAI
from langchain import PromptTemplate
import openai, numpy as np
import google.generativeai as palm

import cohere 
import PyPDF2
import boto3

from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import urllib.parse
from bs4.element import Comment

import json
import os
from dotenv import load_dotenv
import logging
import uuid

import functools
import time
from operator import itemgetter

## Constants
SERVICE_PORT=4001
RUN_GUID='dev'

OPENAI_API_KEY="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"
BING_API_KEY="1e9f7e91959349bc8529239b700cbbcc"
COHERE_API_KEY="J4ATTPxBVb62S3OMRbPP2eqce9ocgYOzEOLM0vHY"
BARD_API_KEY = 'AIzaSyCNlJJDudY5D9qr4v_U1K9FsZYCn4u5m5Q'
BARD_MODEL = 'models/chat-bison-001'

# S3_BUCKET_NAME="tiq-347545"
AWS_ACCESS_KEY="AKIASALBY2Y4H3SMWLVX"
AWS_SECRET_KEY="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"
AWS_REGION="ap-south-1"

# EP_NODE_JOB_CRAWLER="http://127.0.0.1:3001"
EP_NODE_JOB_CRAWLER="https://l08nloaza1.execute-api.ap-south-1.amazonaws.com/latest"
# EP_NODE_ASSESSMENT="http://127.0.0.1:3003"
EP_NODE_ASSESSMENT="https://i8e43d5anj.execute-api.ap-south-1.amazonaws.com/latest"

# SERVICE_REF="postman-dev"
SERVICE_REF="02d45aaa"

# load_dotenv()

# Loggers
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%m-%d-%Y %H:%M:%S')

# file_handler = logging.FileHandler('logs-{}.log'.format(RUN_GUID))
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)

# Wrapper function to measure execution time for any function
# include @timer on top of funtion 
def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        logger.info("[TIMER] Finished {} in {} secs".format(repr(func.__name__), round(run_time, 3)))
        return value
    return wrapper

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

@timer
def text_from_html(url):
    body = urllib.request.urlopen(url).read()    
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(string=True)
    visible_texts = filter(tag_visible, texts)  
    body_text = u" ".join(t.strip() for t in visible_texts)
    logger.info("[PARSER] {}() body_text:: {}".format("text_from_html",body_text))
    return body_text

@timer
def text_from_pdf(_file_s3_bucket, _file_s3_key):
    logger.info("[PARSER] {}() _file_s3_bucket:: {}".format("text_from_html",_file_s3_bucket))
    logger.info("[PARSER] {}() _file_s3_key:: {}".format("text_from_html",_file_s3_key))

    session = boto3.session.Session()
    s3_client = session.client('s3', 
                    region_name=AWS_REGION,
                    aws_access_key_id=AWS_ACCESS_KEY,
                    aws_secret_access_key=AWS_SECRET_KEY)
    _tmp_file_location = "/tmp/{}".format(_file_s3_key.replace("resumes/","")) 
    logger.info("[PARSER] {}() _tmp_file_location:: {}".format("text_from_html",_tmp_file_location))

    s3_client.download_file(_file_s3_bucket,_file_s3_key,_tmp_file_location)
    
    pdfFileObj = open(_tmp_file_location, 'rb')
    reader = PyPDF2.PdfReader(pdfFileObj)
    resume_txt = ""
    for _pgidx in range(len(reader.pages)):
        resume_txt += "\n" + reader.pages[_pgidx].extract_text()
    return resume_txt

@timer
def parse_job_listing(job_listing_txt):
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_job_listing", (len(job_listing_txt.split(" ")))))
    job_listing_txt = (" ").join(job_listing_txt.split(" ")[:500])
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_job_listing", (len(job_listing_txt.split(" ")))))

    # initialize the models
    openai = OpenAI(model_name="text-davinci-003", openai_api_key=OPENAI_API_KEY, temperature=0.0,max_tokens=2000)

    template = """Given a LinkedIn job description, your task is to parse the description and extract the following information and convert to JSON format with keys: seniority_level, employment_type, job_function, industry, job_responsibilities (as a list), skill_requirements (as a list), hiring_manager (including name and designation), educational_requirements (as a list), overall_experience (in years as an integer), and salary_range (as a string). 

    Additional Information: Make sure the skills include only programming-languages. The hiring-manager should be a person name and not organisation name. Keep it blank if unavailable. In educational_requirements include degree_name and field_of_specialisation. Ensure the response has only JSON and no descriptive text.

    Job Description: {joblisting}
    
    The JSON object:
    """

    prompt_template = PromptTemplate(input_variables=["joblisting"], template=template)
    job_listing_json = openai(prompt_template.format(joblisting=job_listing_txt))
    
    # Parse JSON text to object
    job_listing_json = json.loads(job_listing_json)
    logger.info("[PARSER] {}() job_listing_json:: {}".format("parse_job_listing",job_listing_json))
    return job_listing_json

def parse_job_listing_bard(job_listing_txt):
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_job_listing_bard", (len(job_listing_txt.split(" ")))))
    job_listing_txt = (" ").join(job_listing_txt.split(" ")[:2000])
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_job_listing_bard", (len(job_listing_txt.split(" ")))))

    palm.configure(api_key=BARD_API_KEY)
    prompt = """Given a LinkedIn job description, your task is to parse the description and extract the following information and convert to JSON format with keys: seniority_level, employment_type, job_function, industry, job_responsibilities (as a list), skill_requirements (as a list), hiring_manager (including name and designation), educational_requirements (as a list), overall_experience (in years as an integer), salary_range (as a string) and summary as String of 50 words. 

    Job Description: {}
   
    The JSON object:
    """.format(job_listing_txt)

    logger.info("[PARSER] {}() prompt:: {}".format("parse_job_listing_bard", prompt))
    palm_messages = palm.chat(model=BARD_MODEL,messages=prompt,temperature=0.0)
    logger.info("[PARSER] {}() palm_messages:: {}".format("parse_job_listing_bard",palm_messages))
    _res = palm_messages.messages[1]['content']
    json_listing_str = _res.split('```json')[1].replace('```','').replace('\n','').replace('"    "','","').replace('=','')
    logger.info("[PARSER] {}() json_listing_str:: {}".format("parse_job_listing_bard",json_listing_str))
    job_listing_json = json.loads(json_listing_str)
    return job_listing_json

@timer
def questions_for_job_listing(_job_listing_txt, _role, _expertise_level):
    logger.info("[PARSER] {}() word count:: {}".format("questions_for_job_listing", (len(_job_listing_txt.split(" ")))))
    _job_listing_txt = (" ").join(_job_listing_txt.split(" ")[:500])

    # initialize the models
    openai = OpenAI(model_name="text-davinci-003", openai_api_key=OPENAI_API_KEY, temperature=0.0,max_tokens=2000)
    #template = """Given a Job Description, Role, Expertise level, your task is to generate interview questions to assess a candidate for the given {role} and expertise level {expertiselevel}. Generate 10 questions to assess candidate's programming skills, cloud technologies mentioned, provide answers and highlight important keywords for every answer; keywords should include programming languages, frameworks only. Generate response in JSON format with keys: question, answer, keywords as list.
    #template = """Generate 10 interview questions to assess a candidate for the role of {role} with an expertise level of {expertiselevel}. The questions should focus on progrmming skills and cloud technologies mentioned in the following Job Description. For each question, provide an answer and highlight important keywords, including programming languages and frameworks, in the answer. Generate response in JSON format with keys: question, answer, keywords as list.
    #template = """Given a Job Description, Role, Expertise level, your task is to generate 10 interview questions to assess a candidate for the role of {role} and expertise level {expertiselevel}. The questions should focus to assess candidate's programming skills, cloud technologies mentioned, provide answers and highlight important keywords for every answer; keywords should include programming languages, frameworks only. Generate response in JSON format with keys: question, answer, keywords as list.
    template = """Generate 10 interview questions to assess a candidate's knowledge for the role of {role} at this {expertiselevel} level. These questions should evaluate the candidate's technical proficiency and problem-solving skills related to the Job Description, role and expertise level provided. Additionally, provide comprehensive example answers for each question to assist in evaluating the candidate's responses. Generate response in JSON format with keys: question, answer, keywords as list. Generated questions should not be about candidate's experience or purpose.
    Job Description: {joblisting}
    The JSON object:
    """
    prompt_template = PromptTemplate(input_variables=["joblisting","role","expertiselevel"], template=template)
    job_listing_questions_json = openai(prompt_template.format(joblisting=_job_listing_txt,role=_role,expertiselevel=_expertise_level))
    
    logger.info("[PARSER] {}() prompt_template:: {}".format("questions_for_job_listing",prompt_template))

    # Parse JSON text to object
    job_listing_questions_json = json.loads(job_listing_questions_json)
    logger.info("[PARSER] {}() job_listing_questions_json:: {}".format("questions_for_job_listing",job_listing_questions_json))
    return job_listing_questions_json


#@timer
#def questions_for_job_listing_bard(_job_listing_txt, _role, _expertise_level):
    #logger.info("[PARSER] {}() word count:: {}".format("questions_for_job_listing_bard", (len(_job_listing_txt.split(" ")))))
    #_job_listing_txt = (" ").join(_job_listing_txt.split(" ")[:1000])
    
    #bard_api_key = 'AIzaSyCNlJJDudY5D9qr4v_U1K9FsZYCn4u5m5Q'
    #palm.configure(api_key=BARD_API_KEY)
    #model_id = 'models/chat-bison-001'
    
    #prompt="""Given a Job Description, Role, Expertise level, your task is to generate interview questions to assess a candidate for the given role {} and  expertise level {}. Generate minimum 10 questions to assess candidate's programming skills, cloud technoligies mentioned,provide answers and highlight important keywords for every answer; keywords should include programming languages, frameworks only.Generate response in JSON format with keys: question, answer [max 30 words], keywords [max 2 words] as list.and provide directly json response no additional lines like here are the questions that you asked and all.
    #prompt = """Given a Job Description, Role, Expertise level, your task is to generate interview questions to assess a candidate for the given role {} and  expertise level {}. Generate minimum 5 questions to assess candidate's programming skills, cloud technoligies mentioned,provide answers and highlight important keywords for every answer; keywords should include programming languages, frameworks only.Generate response in JSON format with keys: question, answer (max 20 words), keywords (max 2 words) as list.and provide directly json response no additional lines like here are the questions that you asked and all.
    #prompt = """Generate 5 interview questions to assess a candidate's knowledge for the role of {} at {} level. These questions should evaluate the candidate's technical proficiency and problem-solving skills related to the Job Description, role and expertise level provided. Additionally, provide comprehensive example answers for each question to assist in evaluating the candidate's responses. Generate response in JSON format with keys: question, answer, keywords as list. Generated questions should not be about candidate's experience or purpose.
    
    ### Job Description: {}

    ### The JSON object:
    #""".format(_role, _expertise_level, _job_listing_txt)

    #logger.info("[PARSER] {}() prompt:: {}".format("questions_for_job_listing_bard", prompt))
    #palm_messages = palm.chat(model=model_id,messages=prompt,temperature=0.0)
    #logger.info("[PARSER] {}() palm_messages:: {}".format("questions_for_job_listing_bard",palm_messages))
    #job_listing_questions_json = palm_messages.messages[1]['content']
    #_res = palm_messages.messages[1]['content']
    #job_listing_questions_json = json.loads(_res.split('```json')[1].replace('```','').replace('\n',''))
    #return job_listing_questions_json


@timer
def questions_for_job_listing_bard(_job_listing_txt, _role, _expertise_level):
    logger.info("[PARSER] {}() word count:: {}".format("questions_for_job_listing_bard", (len(_job_listing_txt.split(" ")))))
    _job_listing_txt = (" ").join(_job_listing_txt.split(" ")[:1000])
    
    #bard_api_key = 'AIzaSyCNlJJDudY5D9qr4v_U1K9FsZYCn4u5m5Q'
    palm.configure(api_key=BARD_API_KEY)
    model_id = 'models/chat-bison-001'

    #prompt = """Generate 5 interview questions to assess a candidate's knowledge for the role of {} at {} level. These questions should evaluate the candidate's technical proficiency and problem-solving skills related to the Job Description, role and expertise level provided. Additionally, provide comprehensive example answers for each question to assist in evaluating the candidate's responses. Generate response in JSON format with keys: question, answer[max 30 words], keywords[max 2 words] as list. Generated questions should not be about candidate's experience or purpose.
    
    prompt = """Given a Job Description, Role, Expertise level, your task is to generate interview questions to assess a candidate for the given role {}
    and expertise level {}. Generate minimum 5 questions to assess candidate's programming skills, cloud technoligies mentioned,
    provide answers and highlight important keywords for every answer; keywords should include programming languages, frameworks only.
    Generate response in JSON format with keys: question, answer, keywords as list.Directly provide completely terminated json,and no additional lines like 
    here are the questions that you asked and all.
    
    
    ### Job Description: {}

    ### The JSON object:
    """.format(_role, _expertise_level, _job_listing_txt)

    input_token_limit = 1000
    output_token_limit = 2000
    logger.info("[PARSER] {}() prompt:: {}".format("questions_for_job_listing_bard", prompt))
    palm_model = palm.types.Model(name='models/chat-bison-001',base_model_id='chat-bison',version='001', display_name='bard', description='generating parsed response', input_token_limit=input_token_limit,output_token_limit=output_token_limit,supported_generation_methods=['generateMessage'],temperature=0.0,top_p=0.40,top_k=10)
    palm_messages = palm.chat(model=palm_model,messages=prompt,temperature=0.0)
    logger.info("[PARSER] {}() input_tokens:: {}".format("questions_for_job_listing_bard",input_token_limit))
    logger.info("[PARSER] {}() output_tokens:: {}".format("questions_for_job_listing_bard",output_token_limit))
    logger.info("[PARSER] {}() palm_messages:: {}".format("questions_for_job_listing_bard",palm_messages))
    #parser = PydanticOutputParser(pydantic_object=questions_for_job_listing_bard)
    #misformatted = palm_messages.messages[1]['content']
    #job_listing_questions_json = parser.parse(misformatted)
    #job_listing_questions_json = palm_messages.messages[1]['content']
    _res = palm_messages.messages[1]['content']
    job_listing_questions_json = json.loads(_res.split('```json')[1].replace('```','').replace('\n',''))
    return job_listing_questions_json
        
        

@timer
def parse_company_information(_company_information_txt):
    # initialize the models
    openai = OpenAI(model_name="text-davinci-003", openai_api_key=OPENAI_API_KEY,
                    temperature=0.0,max_tokens=200)

    template = """Given a Company Information, your task is to parse the information and extract the following information and convert to JSON. Keep it blank if unavailable. The resulting JSON object should be in this format: company_name:String,ceo_name:String,ceo_approval_rating:String, founded_year:String,company_size:String, revenue:String, industry:String, headquarters:String

    Company Information: {company_information}

    The JSON object:
    """

    prompt_template = PromptTemplate(input_variables=["company_information"], template=template)
    company_information_json = openai(prompt_template.format(company_information=_company_information_txt))
    logger.info("[PARSER] {}() [Before Parsing] company_information_json:: {}".format("parse_company_information",company_information_json))
    
    # Parse JSON text to object
    company_information_json = json.loads(company_information_json)
    logger.info("[PARSER] {}() company_information_json:: {}".format("parse_company_information",company_information_json))
    return company_information_json

@timer
def parse_resume(resume_txt):
    # initialize the models
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_resume", (len(resume_txt.split(" ")))))
    resume_txt = (" ").join(resume_txt.split(" ")[:500])
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_resume", (len(resume_txt.split(" ")))))
    openai = OpenAI(model_name="text-davinci-003",openai_api_key=OPENAI_API_KEY,
                    temperature=0.0, max_tokens=2000)

    template = """Given a resume, your task is to parse the resume and extract  the following information and convert to JSON format with keys:  full_name; date_of_birth; email_id; contact_no; address (as full_address, city, country); overall_experience (as a number); linkedin_url; marital_status; work_experiences as a List of company_name, from_date, to_date, programming_languages as a List, project_details, designation; educational_qualifications as a List of college_or_university_name, degree_name, from_date, to_date; certifications as a List; publications as a List; programming_languages as a List; spoken_languages as a List.

    Additional Information: Make sure the skills include only programming-languages. Keep it blank if information is unavailable. Ensure all dates in YYYY/MM/DD format and the response has only JSON and no descriptive text.

    Resume: {resume}

    The JSON object:
    """

    prompt_template = PromptTemplate(input_variables=["resume"], template=template)
    resume_json = openai(prompt_template.format(resume=resume_txt))
    logger.info("[PARSER] {}() resume_json:: {}".format("parse_resume",resume_json.replace('\n',' ')))
    
    # Parse JSON text to object
    resume_json = json.loads(resume_json)
    return resume_json

# The function first initializes the Palm AI models and then creates a prompt for Bard. The prompt includes the resume text and the list of information to be extracted. The function then calls the Palm AI chat API to generate a response from Bard. The response is a JSON object containing the extracted information. The function then returns the JSON object to the caller.
@timer
def parse_resume_bard(resume_txt):
    # initialize the models
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_resume_bard", (len(resume_txt.split(" ")))))
    resume_txt = (" ").join(resume_txt.split(" ")[:1000])
    logger.info("[PARSER] {}() resume word count:: {}".format("parse_resume_bard", (len(resume_txt.split(" ")))))
    
    palm.configure(api_key=BARD_API_KEY)
    
    # prompt = """Given a resume, your task is to parse the resume and extract  the following information and convert to JSON format with keys:  full_name; date_of_birth; email_id; contact_no; work_experiences as a List of company_name, from_date, to_date, programming_languages as a List, project_details, designation; educational_qualifications as a List of college_or_university_name, degree_name, from_date, to_date; certifications as a List of name and certification_date; publications as a List of name and publication_date; programming_languages as a List; spoken_languages as a List; overall_experience as Integer; summary as String. Ensure all dates in YYYY/MM/DD format.

    prompt = """Given a resume, your task is to parse the resume and extract  the following information and convert to JSON format with keys:  full_name; date_of_birth; email_id; contact_no; work_experiences (max 2) as a List of company_name, from_date, to_date, project_details, designation; educational_qualifications (max 2) as a List of college_or_university_name, degree_name, from_date, to_date; certifications (max 2) as a List of name and certification_date; publications (max 2) as a List of name and publication_date; programming_languages (max 5) as a List; spoken_languages as a List; overall_experience as Integer; summary as String. Ensure all dates in YYYY/MM/DD format.    

    Resume: {}

    The JSON object:
    """.format(resume_txt)    

    logger.info("[PARSER] {}() prompt:: {}".format("parse_resume_bard", prompt))

    palm_messages = palm.chat(model=BARD_MODEL,messages=prompt,temperature=0.0)
    logger.info("[PARSER] {}() palm_messages:: {}".format("parse_resume_bard",palm_messages))
    _res = palm_messages.messages[1]['content']
    resume_json = json.loads(_res.split('```json')[1].replace('```','').replace('\n',''))
    return resume_json

@timer
def enrich_job_listing(job_listing_json):
    # Step 1: Invoking BingAPI to fetch the hiring manager's LinkedIn URL
    if job_listing_json['hiring_manager'] and job_listing_json['hiring_manager']['name'] and job_listing_json['hiring_manager']['designation']:
        search_term = "{} {} site:linkedin.com".format(job_listing_json['hiring_manager']['name'],job_listing_json['hiring_manager']['designation'])
        search_url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        params = {"q": search_term, "textDecorations": True, "textFormat": "HTML"}
        response = requests.get(search_url, headers=headers, params=params)
        search_results = response.json()
    
    if search_results['webPages'] and search_results['webPages']['value'] and len(search_results['webPages']['value']) > 0:
        job_listing_json['hiring_manager']['linkedin_url'] = search_results['webPages']['value'][0]['url']
        
    logger.info("[PARSER] {}() job_listing_json:: {}".format("parse_job_listing",job_listing_json))
    return job_listing_json

@timer
def summarise_job_listing(_job_listing_json):
    cohere_client = cohere.Client(COHERE_API_KEY)
    cohere_res = cohere_client.summarize( 
        text=json.dumps(_job_listing_json),
        length='long',
        format='paragraph',
        model='command',
        additional_command='Focus on company, skills and experience',
        temperature=0,
    ) 
    logger.info("[PARSER] {}() cohere_res:: {}".format("summarise_job_listing",cohere_res))
    return cohere_res.summary

@timer
def summarise_candidate_resume(_resume_json):
    cohere_client = cohere.Client(COHERE_API_KEY)
    cohere_res = cohere_client.summarize( 
        text=json.dumps(_resume_json),
        length='long',
        format='paragraph',
        model='command',
        additional_command='Focus on skills and experience. Do not mention company names.',
        temperature=0,
    ) 
    logger.info("[PARSER] {}() cohere_res:: {}".format("summarise_candidate_resume",cohere_res))
    return cohere_res.summary

@timer
def extract_company_information(_company_name):
    # Step 1: Invoking BingAPI to fetch the hiring manager's LinkedIn URL
    search_term = "{} about company page site:indeed.com".format(_company_name)
    search_url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    params = {"q": search_term, "textDecorations": True, "textFormat": "HTML"}
    response = requests.get(search_url, headers=headers, params=params)
    search_results = response.json()
    indeed_company_about_url = ""
    company_text = ""
    # Check if 'deepLinks' present, else use 1st URL, else 1st Snippet
    if('deepLinks' in search_results['webPages']['value'][0]):
        indeed_company_about_url = search_results['webPages']['value'][0]['deepLinks'][0]['url']
        indeed_company_about_url = ('/').join(indeed_company_about_url.split('/')[:5])
    elif ('url' in search_results['webPages']['value'][0]):
        indeed_company_about_url = search_results['webPages']['value'][0]['url']
        indeed_company_about_url = ('/').join(indeed_company_about_url.split('/')[:5])
    else:
        company_text = search_results['webPages']['value'][0]['snippet']
        logger.info("[PARSER] {}() Snippet >> company_text:: {}".format("extract_company_information",company_text))
    return company_text

############################
# ---- FLASK METHODS ----#
############################

app = Flask(__name__)

# - The BeautifulSoup library is used to parse the HTML content of the LinkedIn job posting page.
# - The HTML content is obtained by sending a request to the LinkedIn job posting URL.
# - BeautifulSoup is then used to extract the relevant text from the HTML, which contains information about the job posting.
@app.route('/v1/joblisting/fetch', methods=['POST'])
def fetch_joblisting(): 
    req = request.get_json()
    _url = req['url']
    job_listing_txt = text_from_html(_url)
    return json.dumps({'success': True, 'data':{'joblisting':job_listing_txt}}), 200, {'ContentType': 'application/json'}

# - The extracted text from the LinkedIn job posting is passed to OpenAI for further processing and analysis.
# - OpenAI's natural language processing capabilities are utilized to extract specific information from the text.
# - The following job details are fetched using OpenAI: seniority_level, employment_type, job_function, industry, 
# job_responsibilities, skill_requirements, hiring_manager, educational_requirements, overall_experience, and salary_range.
@app.route('/v1/joblisting/parse', methods=['POST'])
def parse_joblisting():
    req = request.get_json()
    _joblisting_txt = req['joblisting']
    # Return JSON format
    _joblisting_json = parse_job_listing(_joblisting_txt)
    return json.dumps({'success': True, 'data':{'joblisting':_joblisting_json}}), 200, {'ContentType': 'application/json'}

@app.route('/v2/joblisting/parse', methods=['POST'])
def parse_joblisting_bard():
    req = request.get_json()
    _joblisting_txt = req['joblisting']
    # Return JSON format
    _joblisting_json = parse_job_listing_bard(_joblisting_txt)
    return json.dumps({'success': True, 'data':{'joblisting':_joblisting_json}}), 200, {'ContentType': 'application/json'}

@app.route('/v1/joblisting/questions', methods=['POST'])
def questions_joblisting():
    req = request.get_json()
    _joblisting_txt = req['jobdescription']
    _role = req['role']
    _expertise_level = req['expertiselevel']
    # Return JSON format
    _joblisting_json = questions_for_job_listing(_joblisting_txt, _role, _expertise_level)
    return json.dumps({'success': True, 'data':{'questions':_joblisting_json}}), 200, {'ContentType': 'application/json'}

@app.route('/v2/joblisting/questions', methods=['POST'])
def questions_joblisting_bard():
    req = request.get_json()
    _joblisting_txt = req['jobdescription']
    _role = req['role']
    _expertise_level = req['expertiselevel']
    # Return JSON format
    _joblisting_json = questions_for_job_listing_bard(_joblisting_txt, _role, _expertise_level)
    return json.dumps({'success': True, 'data':{'questions':_joblisting_json}}), 200, {'ContentType': 'application/json'}



# - Once the hiring manager's name is obtained from the job details, the BingAPI is invoked to search for the manager's 
# LinkedIn profile.
# - The BingAPI query includes the name of the hiring manager to find the most relevant LinkedIn profile.
# - The search results from BingAPI provide the URL of the hiring manager's LinkedIn profile, which can be used to access 
# additional information about the manager.
@app.route('/v1/joblisting/enrich', methods=['POST'])
def enrich_joblisting():
    req = request.get_json()
    _joblisting = req['joblisting']
    _joblisting_json = enrich_job_listing(_joblisting)
    return json.dumps({'success': True, 'data':{'joblisting':_joblisting_json}}), 200, {'ContentType': 'application/json'}

# Complete pipeline to parse LinkedIn Job Description
@app.route('/v1/joblisting/linkedin', methods=['POST'])
def linkedin_joblisting():
    req = request.get_json()
    _job_listing = req['job_listing']
    _url = req['job_listing']['url']
    # Using BeautifulSoup to extract text from a LinkedIn job posting
    _joblisting_txt = text_from_html(_url)
    # Parsing the extracted text using OpenAI to fetch various job details
    _joblisting_json = parse_job_listing(_joblisting_txt)
    # Invoking BingAPI to fetch the hiring manager's LinkedIn URL
    _joblisting_json = enrich_job_listing(_joblisting_json)

    _job_listing['seniority_level']=_joblisting_json['seniority_level']
    _job_listing['employment_type']=_joblisting_json['employment_type']
    _job_listing['job_function']=_joblisting_json['job_function']
    _job_listing['industry']=_joblisting_json['industry']
    _job_listing['job_responsibilities']=_joblisting_json['job_responsibilities']
    _job_listing['skill_requirements']=_joblisting_json['skill_requirements']
    _job_listing['educational_requirements']=_joblisting_json['educational_requirements']
    _job_listing['overall_experience']=_joblisting_json['overall_experience']
    _job_listing['salary_range']=_joblisting_json['salary_range']

    logger.info("[PARSER] {}() _job_listing:: {}".format("serp_joblisting",_job_listing))

    # Update Job description with latest information
    url = EP_NODE_JOB_CRAWLER + "/v1/joblisting/" + _job_listing["guid"]
    payload=json.dumps({"joblisting":_job_listing})
    headers = {
        'Content-Type': 'application/json',
        'transaction_guid': str(uuid.uuid4()),
        'service_ref': SERVICE_REF
    }
    requests.request("POST", url, headers=headers, data=payload)

    return json.dumps({'success': True, 'data':{'joblisting':_joblisting_json}}), 200, {'ContentType': 'application/json'}

@app.route('/v1/joblisting/serp', methods=['POST'])
def serp_joblisting():
    req = request.get_json()
    logger.info("[PARSER] {}() req:: {}".format("serp_joblisting",req))

    _job_listing = req['job_listing']
    _joblisting_txt = req['job_listing']['raw_text']
    # Parsing the extracted text using OpenAI to fetch various job details
    _joblisting_json = parse_job_listing(_joblisting_txt)

    _job_listing['seniority_level']=_joblisting_json['seniority_level']
    _job_listing['employment_type']=_joblisting_json['employment_type']
    _job_listing['job_function']=_joblisting_json['job_function']
    _job_listing['industry']=_joblisting_json['industry']
    _job_listing['job_responsibilities']=_joblisting_json['job_responsibilities']
    _job_listing['skill_requirements']=_joblisting_json['skill_requirements']
    _job_listing['educational_requirements']=_joblisting_json['educational_requirements']
    _job_listing['overall_experience']=_joblisting_json['overall_experience']
    _job_listing['salary_range']=_joblisting_json['salary_range']

    logger.info("[PARSER] {}() _job_listing:: {}".format("serp_joblisting",_job_listing))

    # Summarise job-description
    try:
        _job_listing['summary'] = summarise_job_listing(_job_listing)
    except Exception as _exp:
        pass

    # Update Job description with latest information
    url = EP_NODE_JOB_CRAWLER + "/v1/joblisting/" + _job_listing["guid"]
    payload=json.dumps({"joblisting":_job_listing})
    headers = {
        'Content-Type': 'application/json',
        'transaction_guid': str(uuid.uuid4()),
        'service_ref': SERVICE_REF
    }
    requests.request("POST", url, headers=headers, data=payload)

    return json.dumps({'success': True, 'data':{'joblisting':_job_listing}}), 200, {'ContentType': 'application/json'}

@app.route('/v2/joblisting/serp', methods=['POST'])
def serp_joblisting_bard():
    req = request.get_json()
    logger.info("[PARSER] {}() req:: {}".format("serp_joblisting",req))

    _job_listing = req['job_listing']
    _joblisting_txt = req['job_listing']['raw_text']
    # Parsing the extracted text using OpenAI to fetch various job details
    _joblisting_json = parse_job_listing_bard(_joblisting_txt)

    _job_listing['seniority_level']=_joblisting_json['seniority_level']
    _job_listing['employment_type']=_joblisting_json['employment_type']
    _job_listing['job_function']=_joblisting_json['job_function']
    _job_listing['industry']=_joblisting_json['industry']
    _job_listing['job_responsibilities']=_joblisting_json['job_responsibilities']
    _job_listing['skill_requirements']=_joblisting_json['skill_requirements']
    _job_listing['educational_requirements']=_joblisting_json['educational_requirements']
    _job_listing['overall_experience']=_joblisting_json['overall_experience']
    _job_listing['salary_range']=_joblisting_json['salary_range']
    _job_listing['summary']=_joblisting_json['summary']

    logger.info("[PARSER] {}() _job_listing:: {}".format("serp_joblisting",_job_listing))

    # Update Job description with latest information
    url = EP_NODE_JOB_CRAWLER + "/v1/joblisting/" + _job_listing["guid"]
    payload=json.dumps({"joblisting":_job_listing})
    headers = {
        'Content-Type': 'application/json',
        'transaction_guid': str(uuid.uuid4()),
        'service_ref': SERVICE_REF
    }
    requests.request("POST", url, headers=headers, data=payload)

    return json.dumps({'success': True, 'data':{'joblisting':_job_listing}}), 200, {'ContentType': 'application/json'}

@app.route('/v1/company/indeed', methods=['POST'])
def indeed_company_information():
    req = request.get_json()
    logger.info("[PARSER] {}() req:: {}".format("indeed_company_information",req))

    _company = req['company']
    _company_name = req['company']['name']

    # Extract company information as text
    _company_info_txt = extract_company_information(_company_name)
    # Parse information and return JSON
    _company_info_json = parse_company_information(_company_info_txt)

    _company['company_name'] = _company_info_json['company_name']
    _company['company_alias'] = _company_name
    _company['ceo_name'] = _company_info_json['ceo_name']
    _company['ceo_approval_rating'] = _company_info_json['ceo_approval_rating']
    _company['founded_year'] = _company_info_json['founded_year']
    _company['company_size'] = _company_info_json['company_size']
    _company['revenue'] = _company_info_json['revenue']
    _company['industry'] = _company_info_json['industry']
    _company['headquarters'] = _company_info_json['headquarters']
    _company['source'] = 'tiq-crawler'
    _company['company_url'] = ''

    logger.info("[PARSER] {}() _company:: {}".format("indeed_company_information",_company))

    return json.dumps({'success': True, 'data':{'company':_company}}), 200, {'ContentType': 'application/json'}

@app.route('/v1/resume', methods=['POST'])
def resume_parsing():
    req = request.get_json()
    logger.info("[PARSER] {}() req:: {}".format("resume_parsing",req))

    _file_s3_bucket = req['resume']['s3_bucket']
    _file_s3_key = req['resume']['s3_key']
    _request_guid = req['resume']['request_guid']
    _callback_url = req['resume']['callback_url']

    resume_txt = text_from_pdf(_file_s3_bucket, _file_s3_key)
    try:
        resume_json = parse_resume(resume_txt)
        logger.info("[PARSER] {}() >> resume_json:: {}".format("resume_parsing", json.dumps(resume_json)))

        # Summarise job-description
        try:
            resume_json['summary'] = summarise_candidate_resume(resume_json)
        except:
            pass

        # Upsert candidate and attach resume
        url = EP_NODE_ASSESSMENT + "/v1/candidate/resume/parser"
        payload=json.dumps({"resume":resume_json,"request_guid":_request_guid, "callback_url": _callback_url})
        headers = {
            'Content-Type': 'application/json',
            'transaction_guid': str(uuid.uuid4()),
            'service_ref': SERVICE_REF
        }
        requests.request("POST", url, headers=headers, data=payload)
        return json.dumps({'success': True, 'data':{'resume':resume_json}}), 200, {'ContentType': 'application/json'}
    except Exception as _exp:
        print(_exp)
        return json.dumps({'success': False}), 200, {'ContentType': 'application/json'}

# The POST call works as follows:
# - It extracts the text from the resume PDF file using the text_from_pdf() function.
# - It calls the parse_resume_bard() function to parse the resume text and extract the relevant information.
# - It constructs a JSON object containing the extracted resume data.
# - It upserts the candidate and attaches the resume to the candidate record in the assessment system.
# - It sends a POST request to the callback URL with the extracted resume data in the request body.
@app.route('/v2/resume', methods=['POST'])
def resume_parsing_bard():
    req = request.get_json()
    logger.info("[PARSER] {}() req:: {}".format("resume_parsing_bard",req))

    _file_s3_bucket = req['resume']['s3_bucket']
    _file_s3_key = req['resume']['s3_key']
    _request_guid = req['resume']['request_guid']
    _callback_url = req['resume']['callback_url']
    resume_txt = text_from_pdf(_file_s3_bucket, _file_s3_key)
    try:
        resume_json = parse_resume_bard(resume_txt)
        logger.info("[PARSER] {}() >> resume_json:: {}".format("resume_parsing_bard", json.dumps(resume_json)))
        # Upsert candidate and attach resume
        url = EP_NODE_ASSESSMENT + "/v1/candidate/resume/parser"
        payload=json.dumps({"resume":resume_json,"request_guid":_request_guid, "callback_url": _callback_url})
        headers = {
            'Content-Type': 'application/json',
            'transaction_guid': str(uuid.uuid4()),
            'service_ref': SERVICE_REF
        }
        requests.request("POST", url, headers=headers, data=payload)
        return json.dumps({'success': True, 'data':{'resume':resume_json}}), 200, {'ContentType': 'application/json'}
    except Exception as _exp:
        print(_exp)
        return json.dumps({'success': False}), 200, {'ContentType': 'application/json'} 

@app.route('/', methods=['GET'])
def root():
    return json.dumps({ 'success': True}), 200, {'ContentType': 'application/json'}

if __name__ == '__main__':
    app.run(port=SERVICE_PORT)


 
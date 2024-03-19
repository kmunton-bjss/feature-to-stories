import os
from flask import Flask, request, render_template
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

openai_endpoint = os.getenv("OPENAI_ENDPOINT")
openai_deployment = os.getenv("OPENAI_DEPLOYMENT")
openai_key = os.getenv("OPENAI_API_KEY")
client = AzureOpenAI(
    azure_endpoint=openai_endpoint,
    api_key=openai_key,
    api_version="2023-08-01-preview"
)

# Memory cache
queries = {}

app = Flask(__name__)

@app.get("/")
def home():
  return render_template("form.html")

@app.get("/stories")
def stories():
  id = request.args.get("id")
  res = queries.get(id)
  html = res.get("html")
  feature = res.get("feature")
  title = res.get("title")
  return render_template("stories.html", html=html, feature=feature, id=id, title=title)


@app.post("/stories")
def stories_result():
  feature = request.form.get("feature")
  id = str(hash(feature))
  
  # Get cached response
  res = queries.get(id, -1)
  if res != -1:
    return render_template("stories.html", html=res.get("html"), feature=feature, id=id)
  
  completionStories = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.1,
    messages=[
      {
          "role": "system", "content": "Act as a business analyst"
      },
      {
          "role": "user", "content": f"""Create a list of JIRA stories, also known as user stories, 
          based on an application's features. A feature should be broken down into more than one story.
          Describe the acceptance criteria for each story in the given, when and then format.
          
          Return the answer in this HTML format for each story: {HTML_STORIES_FORMAT} 

          The feature is: {feature}"""
      },
    ]
  )
  html = completionStories.choices[0].message.content
  
  completionTitle = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.1,
    messages=[
      {
          "role": "user", "content": f"""Create a title for a feature description and only return the title. 
          Feature description: {feature}"""
      },
    ]
  )
  title = completionTitle.choices[0].message.content
  title = title.replace('"', "")

  # Store in memory cache
  queries[id] = {"html": html, "feature": feature, "title": title, "test": ""}

  return render_template("stories.html", html=html, feature=feature, id=id, title=title)

@app.post("/stories/tests")
def test_code():
  id = request.form.get("id")
  res = queries.get(id)
  title = res.get("title")
  
  # Get cached response
  test = res.get("test")
  if test:
    return render_template("tests.html", html=test, id=id, title=title)
  
  stories = res.get("html")
  completion = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.1,
    messages=[
      {
          "role": "system", "content": "Act as a quality assurance developer"
      },
      {
          "role": "user", "content": f"""Based on stories list comprehensive test scenarios 
          with positive, negative and edge cases based on the acceptance criteria for each story. 
          The tests should cover all types: integration, end-to-end, functional and non-functional tests.
          Make sure there is at least the same number of tests (or more) as the number of acceptance criteria for each story. 
          Include sample test data for each test and create sample code for each test scenario. 
          Use Playwright tool syntax, Jest library syntax and JavaScript ES modules syntax for the sample code.
          
          Return the answer in this HTML format for each test scenario: {HTML_TEST_FORMAT} 

          The stories are: {stories}"""
      },
    ]
  )
  html = completion.choices[0].message.content
  
  # Store in memory cache
  queries[id]["test"] = html
  
  return render_template("tests.html", html=html, id=id, title=title)

HTML_STORIES_FORMAT = """
<h3>Story 1: {{story title}}</h3>
<p>{{ story description }}</p>
<h4>Acceptance Criteria</h4>
<ol>
  <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
  <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
  <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
</ol>
"""

HTML_TEST_FORMAT = """
<h2>{{ Story }}</h2>
<p>{{ Story description }}</p>
<h4>Test scenarios</h4>
<h5>Positive</h5>
<ul>
  <li>
    <p><strong>Given</strong>: {{ given }}</p>
    <p><strong>When</strong>: {{ when }}</p>
    <p><strong>Then</strong>: {{ then }}</p>
    <p><strong>test data</strong>: {{ test data }}</p>
    <pre style="border: 1px solid black; border-radius: 25px; padding: 10px; white-space: pre-wrap;">
      <code>{{ test sample code }}</code>
    </pre>
  </li>
</ul>
<h5>Negative</h5>
<ul>
  <li>
    <p><strong>Given</strong>: {{ given }}</p>
    <p><strong>When</strong>: {{ when }}</p>
    <p><strong>Then</strong>: {{ then }}</p>
    <p><strong>test data</strong>: {{ test data }}</p>
    <pre style="border: 1px solid black; border-radius: 25px; padding: 10px; white-space: pre-wrap;">
      <code>{{ test sample code }}</code>
    </pre>
  </li>
</ul>
<h5>Edge cases</h5>
<ul>
  <li>
    <p><strong>Given</strong>: {{ given }}</p>
    <p><strong>When</strong>: {{ when }}</p>
    <p><strong>Then</strong>: {{ then }}</p>
    <p><strong>test data</strong>: {{ test data }}</p>
    <pre style="border: 1px solid black; border-radius: 25px; padding: 10px; white-space: pre-wrap;">
      <code>{{ test sample code }}</code>
    </pre>
  </li>
</ul>
"""
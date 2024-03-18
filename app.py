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
  return render_template("stories.html", html=html, feature=feature, id=id)


@app.post("/stories")
def stories_result():
  feature = request.form.get("feature")
  id = str(hash(feature))
  
  # Get cached response
  res = queries.get(id, -1)
  if res != -1:
    return render_template("stories.html", html=res.get("html"), feature=feature, id=id)
  
  completion = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.5,
    messages=[
      {
          "role": "system", "content": "Act as a business analyst and a quality assurance engineer."
      },
      {
          "role": "user", "content": f"""Create a list of stories based on a feature. 
          Describe the acceptance criteria for each story in the given, when and then format. 
          List comprehensive test scenarios with positive, negative and edge cases based on the acceptance criteria for each story. 
          Make sure there is at least the same number of tests as the number of acceptance criteria for each story. 
          Include sample test data for each test. 
          
          Return the answer in this HTML format for each story: {HTML_STORIES_FORMAT} 

          The feature is: {feature}"""
      },
    ]
  )
  html = completion.choices[0].message.content

  # Store in memory cache
  queries[id] = {"html": html, "feature": feature, "test": ""}

  return render_template("stories.html", html=html, feature=feature, id=id)

@app.post("/stories/test-code")
def test_code():
  id = request.form.get("id")
  res = queries.get(id)
  
  # Get cached response
  test = res.get("test")
  if test:
    return render_template("test_code.html", html=test, id=id)
  
  stories = res.get("html")
  completion = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.5,
    messages=[
      {
          "role": "system", "content": "Act as a quality assurance developer"
      },
      {
          "role": "user", "content": f"""Based on stories and test scenarios, 
          create sample code for each test scenario. 
          Use Playwright, Jest and JavaScript for the code. 
          
          Return the answer in this HTML format for each test scenario: {HTML_TEST_FORMAT} 

          The stories are: {stories}"""
      },
    ]
  )
  html = completion.choices[0].message.content
  
  # Store in memory cache
  queries[id]["test"] = html

  return render_template("test_code.html", html=html, id=id)

HTML_STORIES_FORMAT = """
<h3>Story 1: {{story title}}</h3>
<p>{{ story description }}</p>
<h4>Acceptance Criteria</h4>
<ol>
  <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
  <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
  <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
</ol>
<h4>End to end test scenarios</h4>
<h5>Positive</h5>
<ul>
  <li>
    <p><strong>scenario</strong>: {{ scenario }}</p>
    <p><strong>expected result</strong>: {{ expected result }}</p>
    <p><strong>test data</strong>: {{ test data }}</p>
  </li>
</ul>
<h5>Negative</h5>
<ul>
  <li>
    <p><strong>scenario</strong>: {{ scenario }}</p>
    <p><strong>expected result</strong>: {{ expected result }}</p>
    <p><strong>test data</strong>: {{ test data }}</p>
  </li>
</ul>
<h5>Edge cases</h5>
<ul>
  <li>
    <p><strong>scenario</strong>: {{ scenario }}</p>
    <p><strong>expected result</strong>: {{ expected result }}</p>
    <p><strong>test data</strong>: {{ test data }}</p>
  </li>
</ul>
"""

HTML_TEST_FORMAT = """
<h2>{{ Test scenario }}</h2>
<p>{{ Test description }}</p>
<pre style="border: 1px solid black; border-radius: 25px; padding: 10px"><code>{{ test code }}</code></pre>
"""
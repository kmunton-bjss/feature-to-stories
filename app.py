import os
from flask import Flask, request, render_template_string, render_template
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

app = Flask(__name__)

@app.get("/")
def home():
  return render_template("form.html")


@app.post("/stories")
def result():
  feature = request.form.get("feature")
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
          
          Return the answer in this HTML format: {HTML_FORMAT} 

          The feature is: {feature}"""
      },
    ]
  )
  html = completion.choices[0].message.content
  return render_template("result.html", html=html)

HTML_FORMAT = """
<h1>Feature {{ feature }}</h1>
<h2>Stories</h2>
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
  <li>{{ scenario and test data }}</li>
  <li>{{ scenario and test data }}</li>
  <li>{{ scenario and test data }}</li>
</ul>
<h5>Negative</h5>
<ul>
  <li>{{ scenario and test data }}</li>
  <li>{{ scenario and test data }}</li>
  <li>{{ scenario and test data }}</li>
</ul>
<h5>Edge cases</h5>
<ul>
  <li>{{ scenario and test data }}</li>
  <li>{{ scenario and test data }}</li>
  <li>{{ scenario and test data }}</li>
</ul>
"""
import os
from flask import Flask, request, render_template, redirect
from openai import AzureOpenAI
from dotenv import load_dotenv
import json
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
ui_queries = {}

app = Flask(__name__)

@app.get("/")
def home():
  return render_template("form.html")

@app.get("/stories")
def stories():
  id = request.args.get("id")
  res = queries.get(id)
  if not res:
    return redirect("/")
  
  html = res.get("html")
  feature = res.get("feature")
  title = res.get("title")
  return render_template("stories.html", html=html, feature=feature, id=id, title=title)


@app.post("/stories")
def stories_result():
  feature = request.form.get("feature")
  if not feature:
    return render_template("error.html", error="Must enter a feature description")
  
  id = str(hash(feature))
  
  # Get cached response
  res = queries.get(id, -1)
  if res != -1:
    return render_template("stories.html", html=res.get("html"), feature=feature, id=id)
  
  completionStories = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.5,
    messages=[
      {
          "role": "system", "content": "Act as a business analyst"
      },
      {
          "role": "user", "content": f"""Breakdown a feature description into individual user stories. 
          A feature should be broken down into two or more user stories. 
          Each user story should have an informative title. 
          Each user story should have a description that follows the format "As a [persona], I [want to], [so that]". 
          Each user story should have several acceptance criteria in the given, when and then format. 
          
          Return the answer in this HTML format for each user story: {HTML_STORIES_FORMAT} 

          The feature is: {feature}"""
      },

    ]
  )
  html = completionStories.choices[0].message.content
  
  completionTitle = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.5,
    messages=[
      {
          "role": "user", "content": f"""Create an informative title 
          for a feature description and only return the title. 
          Feature description: {feature}"""
      },
    ]
  )
  title = completionTitle.choices[0].message.content
  title = title.replace('"', "")

  # Store in memory cache
  queries[id] = {"html": html, "feature": feature, "title": title, "test": ""}

  return render_template("stories.html", html=html, feature=feature, id=id, title=title)

@app.post("/wireframe")
def wireframe_result():
  feature = request.form.get("feature")
  if not feature:
    return render_template("error.html", error="Must enter a UI feature description")
  
  id = str(hash(feature))
  
  # Get cached response
  res = ui_queries.get(id, -1)
  if res != -1:
    return render_template("wireframe.html", url=res.get("url"), feature=feature)
  
  # Change to using DALLE
  client = AzureOpenAI(
    api_version='2024-02-01',
    azure_endpoint=os.getenv('OPENAI_DALLE_ENDPOINT'),
    api_key=os.getenv('OPENAI_DALLE_KEY'),
  )

  message = f"""I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:
     Create a mobile and desktop website wireframes for a weather application that includes these features: {feature}"""

  result = client.images.generate(
    model = 'Dalle3',
    # prompt = f"""Create a website wireframe for a weather application that includes this {feature}""",
    prompt = message,
    quality = 'hd',
    n = 1
  )

  url = json.loads(result.model_dump_json())['data'][0]['url']
  
  # Store in memory cache
  ui_queries[id] = {"url": url}

  return render_template("wireframe.html", url=url, feature=feature)

@app.post("/stories/tests")
def test_code():
  stories_not_found_msg = "Cannot find stories to generate tests from. Go back to home page and start again."
  
  id = request.form.get("id")
  if not id:
    return render_template("error.html", error=stories_not_found_msg)

  res = queries.get(id)
  if not res:
    return render_template("error.html", error=stories_not_found_msg)

  title = res.get("title")
  feature = res.get("feature")
  
  # Get cached response
  test = res.get("test")
  if test:
    return render_template("tests.html", html=test, id=id, title=title, feature=feature)
  
  stories = res.get("html")
  completion = client.chat.completions.create(
    model=openai_deployment, # model = "deployment_name".
    temperature=0.5,
    messages=[
      {
          "role": "system", "content": "Act as a quality assurance developer"
      },
      {
          "role": "user", "content": f"""Based on user stories list comprehensive test scenarios 
          with positive, negative and edge case tests. 
          Base the tests on the acceptance criteria for each story. 
          When appropriate, also include non-functional tests. 
          Make sure there is at least the same number of tests as the number of acceptance criteria for each story. 
          Include sample test data for each test and create sample code for each test scenario. 
          Use Playwright tool syntax, Jest library syntax and JavaScript ES modules syntax for the sample code. 
          
          Return the answer in this HTML format for all test scenarios: {HTML_TEST_FORMAT} 

          The stories are: {stories}"""
      },
    ]
  )
  html = completion.choices[0].message.content
  
  # Store in memory cache
  queries[id]["test"] = html
  
  return render_template("tests.html", html=html, id=id, title=title, feature=feature)

HTML_STORIES_FORMAT = """
<div class="accordion-item">
  <h3 class="accordion-header" id="heading{{ story title }}">
    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#story{{ story title }}" aria-expanded="true" aria-controls="collapseOne">
      Story 1: {{ story title }}
    </button>
  </h3>
  <div id="story{{ story title }}" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#stories">
    <div class="accordion-body">
      <p>{{ story description }}</p>
      <h4>Acceptance Criteria</h4>
      <ol>
        <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
        <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
        <li><strong>given</strong> {{ given }},<strong>when</strong> {{ when }}, <strong>then</strong> {{ then }}</li>
      </ol>
    </div>
  </div>
</div>
"""

HTML_TEST_FORMAT = """
<div class="accordion-item">
  <h3 class="accordion-header" id="heading{{ story title }}">
    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#story{{ story title }}" aria-expanded="true" aria-controls="collapseOne">
      Story 1: {{ story title }}
    </button>
  </h3>
  <div id="story{{ story title }}" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#stories">
    <div class="accordion-body">
      <p class="lead">Positive: {{ test title }}</p>
      <p><strong>Given</strong>: {{ given }}</p>
      <p><strong>When</strong>: {{ when }}</p>
      <p><strong>Then</strong>: {{ then }}</p>
      <p><strong>test data</strong>: {{ test data }}</p>
      <div class="accordion" id="accordion{{ given when then }}>
        <div class="accordion-item">
          <h2 class="accordion-header" id="heading{{ given when then }}">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#code{{ given when then }}" aria-expanded="true" aria-controls="collapseOne">
              See sample test code
            </button>
          </h2>
          <div id="code{{ given when then }}" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#accordion{{ given when then }}">
            <div class="accordion-body">
              <pre style="white-space: pre-wrap;">
                <code>{{ test sample code }}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
      <p class="lead">Negative: {{ test title }}</p>
      <p><strong>Given</strong>: {{ given }}</p>
      <p><strong>When</strong>: {{ when }}</p>
      <p><strong>Then</strong>: {{ then }}</p>
      <p><strong>test data</strong>: {{ test data }}</p>
      <div class="accordion" id="accordion{{ given when then }}>
        <div class="accordion-item">
          <h2 class="accordion-header" id="heading{{ given when then }}">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#code{{ given when then }}" aria-expanded="true" aria-controls="collapseOne">
              See sample test code
            </button>
          </h2>
          <div id="code{{ given when then }}" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#accordion{{ given when then }}">
            <div class="accordion-body">
              <pre style="white-space: pre-wrap;">
                <code>{{ test sample code }}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
      <p class="lead">Edge case: {{ test title }}</p>
      <p><strong>Given</strong>: {{ given }}</p>
      <p><strong>When</strong>: {{ when }}</p>
      <p><strong>Then</strong>: {{ then }}</p>
      <p><strong>test data</strong>: {{ test data }}</p>
      <div class="accordion" id="accordion{{ given when then }}>
        <div class="accordion-item">
          <h2 class="accordion-header" id="heading{{ given when then }}">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#code{{ given when then }}" aria-expanded="true" aria-controls="collapseOne">
              See sample test code
            </button>
          </h2>
          <div id="code{{ given when then }}" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#accordion{{ given when then }}">
            <div class="accordion-body">
              <pre style="white-space: pre-wrap;">
                <code>{{ test sample code }}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
      <p class="lead">Non-functional: {{ test title }}</p>
      <p><strong>Given</strong>: {{ given }}</p>
      <p><strong>When</strong>: {{ when }}</p>
      <p><strong>Then</strong>: {{ then }}</p>
      <p><strong>test data</strong>: {{ test data }}</p>
      <div class="accordion" id="accordion{{ given when then }}>
        <div class="accordion-item">
          <h2 class="accordion-header" id="heading{{ given when then }}">
            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#code{{ given when then }}" aria-expanded="true" aria-controls="collapseOne">
              See sample test code
            </button>
          </h2>
          <div id="code{{ given when then }}" class="accordion-collapse collapse" aria-labelledby="headingOne" data-bs-parent="#accordion{{ given when then }}">
            <div class="accordion-body">
              <pre style="white-space: pre-wrap;">
                <code>{{ test sample code }}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

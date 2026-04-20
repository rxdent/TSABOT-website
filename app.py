from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
import os, json
from pydantic import BaseModel, Field
from typing import Optional

from core_copy.units import UnitManager
from core_copy.progress import ProgressManager

#------------------PREBUILT FUNCTIONS---------------------

unit_manager = UnitManager()
progress_manager = ProgressManager()

#---------------------API STUFF---------------------------

load_dotenv()

app = Flask(__name__)
app.secret_key = "secret_key"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#--------------------------MODELS--------------------------------

class Test_Question(BaseModel):
    question_number: int
    topic_id: str
    question_text: str
    code_snippet: Optional[str] = None  
    options: list[str]
    correct_answer: str

class ScopeCheck(BaseModel):
    related: bool = Field(
        description="True if the message is about Computer Science OR asking about the current unit/topic"
    )
    is_meta: bool = Field(
        description="True if the user is asking about what the bot does, how to use it, or seeking general help/guidance."
    )
    is_summary_request: bool = Field(
        description="True if the student asks for an overview, an explanation of the topic, or 'What is this unit about?'"
    )

#-----------------------FUNCTIONS--------------------------

#GENERATE QUESTIONS------------------------------

def generate_question(used_ids, topic_scope=None):
    valid_ids = []
    scope_context = ""

    for unit in unit_manager.units_data["units"]:
        if topic_scope and topic_scope == unit["id"]:
            valid_ids.extend([s["id"] for s in unit["sections"]])
            scope_context = f"The student is currently being tested on Unit {unit['unit']}: {unit['title']}."
        else:
            for section in unit["sections"]:
                if topic_scope and topic_scope == section["id"]:
                    valid_ids.append(section["id"])
                    scope_context = f"The student is currently being tested on Section: {section['section']}."
                elif not topic_scope:
                    valid_ids.append(section["id"])

    test_prompt = f"""You are a Python technical assessment generator.
{scope_context}

Create ONE multiple-choice question.

Curriculum Data:
{json.dumps(unit_manager.units_data, indent=2)}

VALID TOPIC IDS TO CHOOSE FROM: {', '.join(valid_ids)}

STRICT RULES:
1. The 'topic_id' field MUST be chosen ONLY from the VALID TOPIC IDS list above.
2. Every question must use a unique section ID.
3. Correct Answer Format: A, B, C, or D. Do NOT include A, B, C, or D in the output, just keep in stored.
4. 50% concept questions, 50% logic/code questions.
5. Do NOT reuse used topic IDS: {used_ids}
6. STRICT DATA SEPARATION:
In any LOGIC/CODE questions, follow these rules:

   - 'question_text' must ONLY contain the natural language question (e.g., "What is the output of this code?" or "Which choice correctly fills the gap?").
   - 'code_snippet' must contain ALL code, including variable assignments, function definitions, or logic mentioned in the prompt.
   - DO NOT describe code inside the text. 
     BAD: "If x = 10, what is printed?" 
     GOOD: Text: "What is the output?" | Code: "x = 10\nprint(x)"
7. Do NOT reuse used topic IDS: {used_ids}

Return JSON ONLY in this format:
{{
  "question_number": 1,
  "topic_id": "...",
  "question_text": "...",
  "code_snippet": "x = 5\\nprint(x + 2)",
  "options": ["...", "...", "...", "..."],
  "correct_answer": "A"
}}

Output must be valid JSON. Do not include ```json at the beginning of your line. It must be raw JSON code.
"""

    response = client.chat.completions.parse(
        model="gpt-4o-mini",
        response_format=Test_Question,
        messages=[
            {"role": "system", "content": test_prompt},
            {"role": "user", "content": "Generate the next question now."}
        ]
    )
    
    return json.loads(response.choices[0].message.content)

#CHECK IF USER MESSAGE IS RELATED TO THE TOPIC IN STUDY MODE--------------

def check_if_related(user_message, unit_info):
    prompt = f"""
    You are a classification assistant for a TSA Computer Science tutor.
    CURRENT UNIT: {unit_info["unit"]}
    CURRENT TOPIC: {unit_info["section"]}

    CLASSIFICATION RULES:
    1. Set related = true if the user asks about coding OR asks about your capabilities (e.g., "What can you do?").
    2. Set is_meta = true if they are asking about you, the unit structure, or general help.
    3. Set is_summary_request = true if they want a broad explanation of the current unit or topic.
    
    If they ask about unrelated topics like sports, food, or general chat, set all to False.
    """
    
    response = client.chat.completions.parse(
        model="gpt-4o-mini",
        response_format=ScopeCheck,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.parsed

#AI RESPONSE TO USER PROMPTS IN STUDY MODE---------------------------

def bot_reply(user_message, unit_info):
    prompt = f"""
    You are a TSA study assistant. 
    CURRENT UNIT: {unit_info["unit"]}
    CURRENT TOPIC: {unit_info["section"]}

    Rules:
    - Use bullet points for lists.
    - No markdown (no bold, no italics).
    - 2 to 4 sentences max.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content


#----------------------FLASK ROUTES--------------------------

#HOME PAGE---------------------

@app.route("/")
def home():
    return render_template("home.html", mode="home")

#TEST HOME PAGE----------------------------------

@app.route("/test_mode")
def test_selection():
    return render_template("testmode.html", units_data=unit_manager.units_data, mode="test")

#PRACTICE HOME PAGE------------------------------

@app.route("/practice")
def practice_selection():
    return render_template("practicetest.html", units_data=unit_manager.units_data, mode="practice")

#CHOOSE A MODE (Test/practice) PAGE ------------------------

@app.route("/test/start/<mode>/<scope>")
def start_test(mode, scope):
    session["questions"] = []
    session["current_question"] = 0
    session["answers"] = {}
    session["feedback_shown"] = {}
    session["used_topic_ids"] = []
    session["mode"] = mode
    session["test_scope"] = None if scope == "all" else scope
    
    if "-" in scope:
        session["total_questions"] = 3
    elif scope.startswith("U"):
        session["total_questions"] = 5
    else:
        session["total_questions"] = 10
        
    return redirect(url_for("question"))

#GENERATE QUESTION PAGE----------------

@app.route("/test/question")
def question():
    # 🔴 NEW: handle sidebar jump
    go_to = request.args.get("go")
    if go_to is not None:
        session["current_question"] = int(go_to)

    questions = session.get("questions", [])
    index = session.get("current_question", 0)
    total = session.get("total_questions", 10)
    mode = session.get("mode")

    if index >= total:
        return redirect(url_for("results"))
    
    if index >= len(questions):
        used_ids = session.get("used_topic_ids", [])
        scope = session.get("test_scope")

        while len(questions) <= index:
            new_q = generate_question(used_ids, topic_scope=scope)
            questions.append(new_q)
            used_ids.append(new_q["topic_id"])

        session["questions"] = questions
        session["used_topic_ids"] = used_ids
        session.modified = True

    q = questions[index]
    answers = session.get("answers", {})
    feedback_shown = session.get("feedback_shown", {})
        
    selected = answers.get(str(index))

    is_correct = None
    if selected:
        is_correct = (selected == q["correct_answer"])

    show_feedback = (mode == "practice" and feedback_shown.get(str(index)))

    return render_template(
        "test.html",
        q=q,
        index=index,
        selected=selected,
        questions=questions,
        mode=mode,
        show_feedback=show_feedback,
        is_correct=is_correct
    )

#SHOW ANSWER (if in practice mode) + NAVIGATION SYSTEM------

@app.route("/test/answer", methods=["POST"])
def answer():
    selected = request.form.get("answer")
    direction = request.form.get("direction")
    index = session["current_question"]
    mode = session.get("mode")

    answers = session.get("answers", {})
    feedback_shown = session.get("feedback_shown", {})

    if selected:
        answers[str(index)] = selected.upper()
        session["answers"] = answers

    if direction == "next":
        session["current_question"] = index + 1
        return redirect(url_for("question"))

    if direction == "back":
        session["current_question"] = max(0, index - 1)
        return redirect(url_for("question"))

    if mode == "practice":
        if not feedback_shown.get(str(index)):
            feedback_shown[str(index)] = True
            session["feedback_shown"] = feedback_shown
            return redirect(url_for("question"))

        session["current_question"] = index + 1
        return redirect(url_for("question"))

    if mode == "test":
        session["current_question"] = index + 1
        return redirect(url_for("question"))

    return redirect(url_for("question"))

#RESULTS PAGE------------------------------

@app.route("/test/results")
def results():
    mode = session.get("mode")
    questions = session.get("questions", [])
    answers = session.get("answers", {})
    results_list = []
    score = 0

    for i, q in enumerate(questions):
        selected = answers.get(str(i))
        correct = q["correct_answer"]
        is_correct = (selected == correct)
        if mode == "test":
            if is_correct:
                score += 1
            progress_manager.update(q["topic_id"], is_correct)

        results_list.append({
            "question": q["question_text"],
            "options": q["options"],
            "your_answer": selected,
            "correct_answer": correct,
            "is_correct": is_correct
            })


    progress_manager.save()

    #frontend
    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0

    return render_template(
        "results.html", 
        score=score, 
        total=total, 
        percentage=percentage, 
        results=results_list,
        mode=mode
    )

#STUDY MODE PAGE-----------------------------

@app.route("/study")
def study_home():
    return render_template(
        "study.html",
        units_data=unit_manager.units_data,
        mode="study",
        view="main"
    )


@app.route("/study/guide")
def study_guide():
    return render_template(
        "study.html",
        units_data=unit_manager.units_data,
        mode="study",
        view="guide"
    )


@app.route("/study/weak") #FIX THIS!!!!!!!!!!!
def study_weak():
    weak_ids = progress_manager.data.get("weak_topics", [])

    # Build filtered units structure
    filtered_units = {"units": []}

    for unit in unit_manager.units_data["units"]:
        matching_sections = [
            s for s in unit["sections"] if s["id"] in weak_ids
        ]

        if matching_sections:
            filtered_units["units"].append({
                "unit": unit["unit"],
                "title": unit["title"],
                "id": unit["id"],
                "sections": matching_sections
            })

    return render_template(
        "study.html",
        units_data=filtered_units,
        mode="study",
        view="weak"
    )

#AI INTERFACE----------------------------------------

@app.route("/study/chat", methods=["POST"])
def study_chat():
    user_msg = request.json.get("message")
    topic_id = request.json.get("topic")
    unit_info = unit_manager.get_name(topic_id)

    check = check_if_related(user_msg, unit_info)

    if not (check.related or check.is_meta):
        return {"response": "I can't answer that question. What else can I help you with?"}

    # if check.is_summary_request:
    #     answer = generate_summary_reply(user_msg, unit_info)
    else:
        # Standard coding explanation
        answer = bot_reply(user_msg, unit_info)
    
    return {"response": answer}

if __name__ == "__main__":
    app.run(debug=True)
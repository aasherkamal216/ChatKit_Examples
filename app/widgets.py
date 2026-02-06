# app/widgets.py
from chatkit.widgets import Card, Text, Button, Input, Form, Row, Col, Title

def build_weather_widget(location: str, temperature: int, condition: str):
    """Builds a card showing weather info."""
    return Card(
        children=[
            Title(value=f"Weather in {location}"),
            Text(value=f"{temperature}°F, {condition}", size="lg"),
            Text(value="Wear a jacket if you go out!", color="secondary"),
        ]
    )

def build_feedback_form():
    """Builds an interactive form."""
    return Card(
        asForm=True,
        children=[
            Form(
                onSubmitAction={
                    "type": "submit_feedback",
                    "payload": {} # Form inputs auto-merge into payload
                },
                children=[
                    Title(value="Feedback"),
                    Text(value="How was your experience today?"),
                    Input(name="user_comment", placeholder="Type here...", required=True),
                    Button(label="Submit Feedback", submit=True)
                ]
            )
        ]
    )
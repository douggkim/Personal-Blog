from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditor, CKEditorField

class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired("Please Enter Your Email"), Email("Please enter "
                                                                                            "your email "
                                                                                            "address.")])
    password = PasswordField("Password", validators=[DataRequired("Please Enter a passowrd")])
    name = StringField("Name", validators=[DataRequired("Please enter your name")])
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired("Please Enter Your Email"), Email("Please enter "
                                                                                            "your email "
                                                                                            "address.")])
    password = PasswordField("Password", validators=[DataRequired("Please Enter a passowrd")])
    submit = SubmitField("Login")

class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Write")
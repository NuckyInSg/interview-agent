import os
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
import re

class SoftwareInterviewAgent:
    def __init__(self, api_key, resume_path, job_description_path, model="claude-3-sonnet-20240229", api_url="https://api.anthropic.com"):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.resume_path = resume_path
        self.job_description_path = job_description_path
        
        self.prompt = """
        You are Dolores, an expert IT manager conducting a job interview for a software engineering position. You have access to the candidate's resume and the job description. Conduct a realistic and professional interview following these stages:

        1. Introduction and small talk, interview_stage = introduction
        2. Overview of the candidate's background, interview_stage = overview
        3. Technical questions related to the job requirements, interview_stage = technical
        4. Project or experience deep dive, interview_stage = project
        5. Company and role-specific questions, interview_stage = company
        6. Candidate's questions for the interviewer, interview_stage = candidate
        7. Closing remarks, interview_stage = closing

        Throughout the interview, maintain a professional and friendly tone. Ask relevant questions based on the resume and job requirements. Provide thoughtful responses and follow-up questions based on the candidate's answers.

        Use the following format for each stage:
        <interview_stage>
        [Name of the stage]
        </interview_stage>

        <interviewer>
        [Your question or statement]
        </interviewer>

        Resume:
        {resume_content}

        Job Description:
        {job_content}

        Remember to adapt your questions and conversation based on the candidate's responses and ensure technical questions are appropriate for the position level.
        """
        
        self.llm = ChatAnthropic(
            anthropic_api_url=self.api_url,
            model=self.model,
            temperature=0,
            api_key=self.api_key
        )
        
        self.resume_content, self.job_content = self._load_documents()
        self.interview_chain = self._create_interview_chain()

    def _load_documents(self):
        resume_loader = PyPDFLoader(self.resume_path)
        job_loader = TextLoader(self.job_description_path)
        
        resume_data = resume_loader.load()
        job_data = job_loader.load()
        
        text_splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        resume_docs = text_splitter.split_documents(resume_data)
        job_docs = text_splitter.split_documents(job_data)
        
        resume_content = " ".join([doc.page_content for doc in resume_docs])
        job_content = " ".join([doc.page_content for doc in job_docs])
        
        return resume_content, job_content

    def _create_interview_chain(self):
        system_template = self.prompt.format(
            resume_content=self.resume_content,
            job_content=self.job_content
        )
        
        human_template = "{input}"

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", human_template)
        ])

        chain = chat_prompt | self.llm | StrOutputParser()

        store = {}

        def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in store:
                store[session_id] = InMemoryChatMessageHistory()
            return store[session_id]

        return RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    @staticmethod
    def extract_interviewer_content(text):
        pattern = r'<interviewer>(.*?)</interviewer>'
        matches = re.findall(pattern, text, re.DOTALL)
        return '\n'.join(match.strip() for match in matches)

    @staticmethod
    def extract_interview_stage(text):
        pattern = r'<interview_stage>(.*?)</interview_stage>'
        matches = re.findall(pattern, text, re.DOTALL)
        return '\n'.join(match.strip() for match in matches)

    def conduct_interview(self, session_id):
        config = {"configurable": {"session_id": session_id}}

        # Initialize the conversation
        response = self.interview_chain.invoke(
            {
                "input": "Start the interview with the introduction and small talk stage."
            },
            config=config
        )
        stage = self.extract_interview_stage(response['text'])
        interviewer_content = self.extract_interviewer_content(response['text'])
        print(f"Stage: {stage}")
        print(f"Interviewer: {interviewer_content}")

        # Main interview loop
        while True:
            answer = input("Candidate: ")
            if answer.lower() == 'end interview':
                break

            response = self.interview_chain.invoke(
                {
                    "input": f"The candidate's response: {answer}\nContinue the interview based on the current stage and the candidate's response."
                },
                config=config
            )
            stage = self.extract_interview_stage(response['text'])
            interviewer_content = self.extract_interviewer_content(response['text'])
            print(f"Stage: {stage}")
            print(f"Interviewer: {interviewer_content}")

        # Closing remarks
        response = self.interview_chain.invoke(
            {
                "input": "Provide closing remarks and explain the next steps in the hiring process."
            },
            config=config
        )
        stage = self.extract_interview_stage(response['text'])
        interviewer_content = self.extract_interviewer_content(response['text'])
        print(f"Stage: {stage}")
        print(f"Interviewer: {interviewer_content}")

if __name__ == "__main__":
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    resume_path = "./my_resume.pdf"
    job_description_path = "meta_jd.txt"

    agent = SoftwareInterviewAgent(api_key, resume_path, job_description_path)
    agent.conduct_interview("interview_session_1")
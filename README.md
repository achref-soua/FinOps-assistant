# 💸 FinOps Assistant (Streamlit App)

A **Streamlit-based FinOps tool** that helps you optimize costs and manage workloads on **AWS EC2** and **AWS RDS**.  
The app provides recommendations, pricing comparisons, and insights to support cloud financial operations (FinOps).  

---

## 🚀 Features

### 🖥️ EC2 Optimization
- 🔑 Connect using AWS credentials **or** upload a CSV / enter instances manually.  
- 📊 Analyze your **active EC2 instances**.  
- ⚡ Suggest the closest **Graviton equivalent** for cost savings.  
- 💰 Filter and highlight the **cheapest options** available.  
- 🗓️ Detect **scheduled events** (e.g., retirement notifications).  

### 🗄️ RDS Reservation Insights
- 🔑 Input data via a **form**, JSON upload, or manual entry.  
- 📅 Provide start & end dates of reservations.  
- 📊 Get all possible **pricing & savings scenarios**:
  - On-Demand (No reserve)  
  - Reserved Instances: **No upfront / Partial upfront / Full upfront**  
- 💡 See potential **economies & comparisons** between options.  

---

## 🛠️ Tech Stack
- **[Python](https://www.python.org/)**  
- **[Streamlit](https://streamlit.io/)**  
- **[AWS SDK (boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)**  

---

## ⚙️ Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/achref-soua/finops-assistant.git
   cd finops-assistant
   ```

2. Create & activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / Mac
   venv\Scripts\activate      # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Usage

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Open in your browser:  
   👉 `http://localhost:8501`

---

## 📁 Project Structure
```
finops-assistant/
│── app.py              # Main Streamlit app entry point
│── requirements.txt    # Python dependencies
│── README.md           # Documentation
│── .gitignore          # Ignored files (e.g., .env, __pycache__)
│── .env                # AWS credentials (not in repo)
│
├── app_pages/          # Streamlit page modules
│   ├── home.py
│   ├── ec2_analysis.py
│   └── rds_analysis.py
│
├── assets/             # Static files (images, icons, etc.)
│   └── moovto.png
│
└── utils/              # Helper functions and modules
    ├── auth.py
    ├── helpers.py
    ├── models.py
    └── pricing.py
```

---

## 🔒 Security
- AWS credentials are never stored in the repo.  
- Use a **.env file** (already gitignored) to manage secrets safely.  

---

## 🧑‍💻 Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you’d like to improve.  

---

## 📜 License
This project is licensed under the **MIT License**.  

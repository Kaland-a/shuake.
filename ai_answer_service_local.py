"""
网课自动答题 AI 服务 - 使用本地模型版本
支持直接加载本地模型，无需Ollama
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI答题服务 - 本地模型版")

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 配置区域 - 请根据您的实际情况修改
# ============================================================

# 模型路径配置
MODEL_CONFIG = {
    # 选项1: 使用本地路径（推荐）
    "model_path": r"C:\Users\bdjk\.cache\modelscope\hub\models\Qwen\Qwen2.5-1.5B-Instruct",  # 模型存储路径
    
    # 选项2: 从Hugging Face下载（如果本地没有）
    # "model_path": "Qwen/Qwen2.5-7B-Instruct",
    
    # 其他可选千问模型：
    # "model_path": "Qwen/Qwen2.5-3B-Instruct",
    # "model_path": "Qwen/Qwen2.5-1.5B-Instruct",
    # "model_path": "Qwen/Qwen2.5-14B-Instruct",
    # "model_path": "Qwen/Qwen2.5-72B-Instruct",
    # "model_path": r"D:\models\qwen2.5-14b-instruct",
    
    # 模型加载参数
    "device_map": "auto",  # 自动分配设备（CPU/GPU）
    "torch_dtype": torch.float16,  # 使用半精度（如果GPU不支持，改为torch.float32）
    
    # 生成参数
    "max_new_tokens": 256,
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 40,
}

# ============================================================
# 全局模型变量
# ============================================================
tokenizer = None
model = None

class QuestionRequest(BaseModel):
    question: str
    options: Optional[List[str]] = []
    type: str  # 0:单选 1:多选 3:判断 2:填空 4:简答
    questionData: Optional[str] = ""
    workType: Optional[str] = ""
    id: Optional[str] = ""
    key: Optional[str] = ""

class AnswerResponse(BaseModel):
    code: int
    data: dict
    msg: str

def load_model():
    """加载模型（启动时调用一次）"""
    global tokenizer, model
    
    try:
        logger.info(f"开始加载模型: {MODEL_CONFIG['model_path']}")
        logger.info("这可能需要几分钟，请耐心等待...")
        
        # 加载分词器
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_CONFIG['model_path'],
            trust_remote_code=True
        )
        
        # 加载模型
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_CONFIG['model_path'],
            device_map=MODEL_CONFIG['device_map'],
            torch_dtype=MODEL_CONFIG['torch_dtype'],
            trust_remote_code=True
        )
        
        # 设置为评估模式
        model.eval()
        
        logger.info("✓ 模型加载成功！")
        logger.info(f"设备: {next(model.parameters()).device}")
        logger.info(f"精度: {next(model.parameters()).dtype}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 模型加载失败: {e}")
        logger.error("请检查:")
        logger.error("1. 模型路径是否正确")
        logger.error("2. 模型文件是否完整")
        logger.error("3. Python内存是否足够")
        return False

def generate_answer(prompt: str) -> str:
    """使用模型生成答案"""
    try:
        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专业的答题助手，请直接给出准确答案，不要添加额外解释。"},
            {"role": "user", "content": prompt}
        ]
        
        # 应用聊天模板
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            enable_thinking=False,
            add_generation_prompt=True
        )
        
        # 编码
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        
        # 生成
        with torch.no_grad():
            generated_ids = model.generate(
                **model_inputs,
                max_new_tokens=MODEL_CONFIG['max_new_tokens'],
                temperature=MODEL_CONFIG['temperature'],
                top_p=MODEL_CONFIG['top_p'],
                top_k=MODEL_CONFIG['top_k'],
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # 解码（只取新生成的部分）
        generated_ids = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response.strip()
        
    except Exception as e:
        logger.error(f"生成错误: {e}")
        return ""

def parse_answer(answer_text: str, q_type: str, options: List[str]) -> List[str]:
    """解析AI返回的答案"""
    
    # 添加这3行调试日志
    logger.info(f"[解析] 答案文本: {answer_text}")
    logger.info(f"[解析] 选项数量: {len(options)}")
    logger.info(f"[解析] 选项内容: {options}")
    
    # 在函数开头添加选项清理
    cleaned_options = []
    for opt in options:
        # 去掉选项前的 A. B. C. D. 等标记
        clean = re.sub(r'^[A-Z]\.?\s*', '', str(opt).strip())
        cleaned_options.append(clean)

    logger.info(f"[解析] 清理后的选项: {cleaned_options}")

    # 然后用 cleaned_options 替换 options
    options = cleaned_options
    
    if q_type == "0":  # 单选题
        match = re.search(r'([A-Z])', answer_text)
        if match:
            letter = match.group(1)
            idx = ord(letter) - 65
            logger.info(f"[解析] 找到字母: {letter}, 索引: {idx}, 选项总数: {len(options)}")
            
            # 如果有选项列表，返回选项内容
            if options and 0 <= idx < len(options):
                result = options[idx]
                logger.info(f"[解析成功] 字母{letter} -> 选项: {result}")
                return [result]
            # 如果没有选项列表，直接返回字母
            else:
                logger.info(f"[解析成功] 返回字母: {letter}")
                return [letter]
        return []
    
    elif q_type == "1":  # 多选题
        letters = re.findall(r'([A-Z])', answer_text)
        logger.info(f"[解析] 找到的字母: {letters}")
        
        # 如果有选项列表
        if options:
            answers = []
            for letter in letters:
                idx = ord(letter) - 65
                if 0 <= idx < len(options):
                    answers.append(options[idx])
            return answers if answers else []
        # 如果没有选项列表，直接返回字母列表
        else:
            logger.info(f"[解析成功] 返回字母列表: {letters}")
            return letters
    
    elif q_type == "3":  # 判断题
        lower = answer_text.lower()
        if "正确" in answer_text or "true" in lower or "对" in answer_text or "yes" in lower:
            return ["正确"]
        elif "错误" in answer_text or "false" in lower or "错" in answer_text or "no" in lower:
            return ["错误"]
        return []
    
    else:  # 填空题、简答题等
        answer_text = answer_text.replace("答案：", "").replace("答案:", "").strip()
        # 移除常见的前缀
        answer_text = re.sub(r'^(答案?[:：]?\s*)', '', answer_text)
        return [answer_text] if answer_text else []

@app.on_event("startup")
async def startup_event():
    """启动时加载模型"""
    logger.info("=" * 60)
    logger.info("AI答题服务启动中...")
    logger.info("=" * 60)
    
    success = load_model()
    
    if not success:
        logger.error("模型加载失败，服务将以错误模式运行")
        logger.error("请修改 MODEL_CONFIG 中的 model_path")
    else:
        logger.info("=" * 60)
        logger.info("✓ 服务启动成功！")
        logger.info(f"API地址: http://localhost:5000")
        logger.info(f"API文档: http://localhost:5000/docs")
        logger.info("=" * 60)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI答题服务运行中",
        "status": "ok" if model is not None else "error",
        "model_loaded": model is not None,
        "model_path": MODEL_CONFIG['model_path']
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    return {
        "status": "healthy",
        "model": MODEL_CONFIG['model_path'],
        "device": str(next(model.parameters()).device)
    }
    
@app.post("/search")
async def search_answer(request: QuestionRequest):
    """答题接口（兼容脚本格式） - 已修复繁体中文题型识别问题"""
    
    # 添加这行日志，查看前端传来的选项
    logger.info(f"[请求] 收到的选项列表: {request.options}")
    
    # 检查模型是否加载
    if model is None or tokenizer is None:
        return AnswerResponse(
            code=10003,
            data={"answer": [], "num": "", "usenum": ""},
            msg="模型未加载，请检查配置"
        )
    
    try:
        # ============================================================
        # 1. 题型标准化映射 (核心修复部分)
        # ============================================================
        # 将各种输入(繁体/简体/数字)统一映射为内部代码
        NORMALIZE_TYPE_MAP = {
            # 单选题 -> "0"
            "0": "0", "单选题": "0", "單選題": "0", "单选": "0", "單選": "0", "Single": "0",
            # 多选题 -> "1"
            "1": "1", "多选题": "1", "多選題": "1", "多选": "1", "多選": "1", "Multiple": "1",
            # 填空题 -> "2"
            "2": "2", "填空题": "2", "填空題": "2", "填空": "2",
            # 判断题 -> "3"
            "3": "3", "判断题": "3", "判斷題": "3", "判断": "3", "判斷": "3", "TrueOrFalse": "3",
            # 简答题 -> "4"
            "4": "4", "简答题": "4", "簡答題": "4", "简答": "4", "簡答": "4",
            # 名词解释 -> "5"
            "5": "5", "名词解释": "5", "名詞解釋": "5",
            # 论述题 -> "6"
            "6": "6", "论述题": "6", "論述題": "6",
            # 计算题 -> "7"
            "7": "7", "计算题": "7", "計算題": "7"
        }

        # 获取标准化的题型代码 (如果没找到，默认当做简答题"4"处理，避免报错)
        # strip() 去除可能存在的空格
        raw_type = str(request.type).strip()
        standard_type = NORMALIZE_TYPE_MAP.get(raw_type, "4")

        # 用于显示给 LLM 的中文名称
        type_name_map = {
            "0": "单选题",
            "1": "多选题",
            "3": "判断题",
            "2": "填空题",
            "4": "简答题",
            "5": "名词解释",
            "6": "论述题",
            "7": "计算题"
        }
        
        q_type_name = type_name_map.get(standard_type, "简答题")
        
        # ============================================================
        # 2. 构建 Prompt
        # ============================================================
        prompt = f"""请仔细分析以下题目并给出正确答案。

题目类型: {q_type_name}
题目: {request.question}
"""
        
        if request.options:
            prompt += "\n选项:\n"
            for i, opt in enumerate(request.options):
                # 清理选项内容，防止格式混乱
                clean_opt = str(opt).strip()
                prompt += f"{chr(65+i)}. {clean_opt}\n"
        
        # 根据标准化后的题型添加特定指令
        prompt += "\n请直接给出答案，不要添加任何解释：\n"
        if standard_type == "0":
            prompt += "- 单选题：只回答一个选项字母，如 A"
        elif standard_type == "1":
            prompt += "- 多选题：回答所有正确选项字母，用逗号分隔，如 A,C,D"
        elif standard_type == "3":
            prompt += "- 判断题：只回答'正确'或'错误'"
        else:
            prompt += "- 填空或简答：直接给出答案内容"

        prompt += "\n\n答案："
        
        logger.info(f"[答题] 原始类型: {raw_type} -> 识别为: {q_type_name} ({standard_type})")
        logger.info(f"[答题] 题目: {request.question[:50]}...")
        
        # ============================================================
        # 3. 生成与解析
        # ============================================================
        ai_answer = generate_answer(prompt)
        logger.info(f"[答题] AI回答: {ai_answer}")
        
        # 使用标准化后的 standard_type 进行解析，确保解析逻辑正确
        answers = parse_answer(ai_answer, standard_type, request.options)
        
        if answers:
            logger.info(f"[答题] 解析结果: {answers}")
            return AnswerResponse(
                code=200,
                data={
                    "answer": answers,
                    "num": "Local AI",
                    "usenum": "本地模型"
                },
                msg="答题成功"
            )
        else:
            logger.warning("[答题] 无法解析答案")
            # 即使解析失败，对于非选择题也尝试直接返回AI的原始回答
            if standard_type not in ["0", "1", "3"]:
                 return AnswerResponse(
                    code=200,
                    data={
                        "answer": [ai_answer],
                        "num": "Local AI",
                        "usenum": "本地模型"
                    },
                    msg="答题成功(未格式化)"
                )

            return AnswerResponse(
                code=10003,
                data={"answer": [], "num": "", "usenum": ""},
                msg="AI无法解答此题"
            )
    
    except Exception as e:
        logger.error(f"[答题] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return AnswerResponse(
            code=10003,
            data={"answer": [], "num": "", "usenum": ""},
            msg=f"服务错误: {str(e)}"
        )
@app.post("/test")
async def test_generate(prompt: str = "你好"):
    """测试生成功能"""
    if model is None:
        return {"error": "模型未加载"}
    
    response = generate_answer(prompt)
    return {
        "prompt": prompt,
        "response": response
    }

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 AI答题服务 - 本地模型版")
    print("=" * 60)
    print(f"📁 模型路径: {MODEL_CONFIG['model_path']}")
    print(f"🔧 设备模式: {MODEL_CONFIG['device_map']}")
    print(f"💾 数据类型: {MODEL_CONFIG['torch_dtype']}")
    print("=" * 60)
    print("⏳ 正在启动服务...")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )

"""
Advanced synthetic data generator with realistic attack chains and MITRE ATT&CK mapping.
"""

import random
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

# MITRE ATT&CK Tactics
TACTICS = [
    "TA0043: Reconnaissance",
    "TA0042: Resource Development",
    "TA0001: Initial Access",
    "TA0002: Execution",
    "TA0003: Persistence",
    "TA0004: Privilege Escalation",
    "TA0005: Defense Evasion",
    "TA0006: Credential Access",
    "TA0007: Discovery",
    "TA0008: Lateral Movement",
    "TA0009: Collection",
    "TA0010: Exfiltration",
    "TA0011: Command and Control"
]

# Техники атак с рекомендациями
ATTACK_TECHNIQUES = {
    "T1059.001": {
        "name": "PowerShell",
        "tactic": "Execution",
        "recommendation": "Включить Script Block Logging и Constrained Language Mode",
        "severity": "HIGH"
    },
    "T1055.001": {
        "name": "Process Hollowing",
        "tactic": "Defense Evasion",
        "recommendation": "Включить защиту процессов (PPL) и мониторинг создания процессов",
        "severity": "HIGH"
    },
    "T1003.001": {
        "name": "LSASS Memory Dump",
        "tactic": "Credential Access",
        "recommendation": "Включить Credential Guard и LSA Protection",
        "severity": "CRITICAL"
    },
    "T1046": {
        "name": "Network Service Scanning",
        "tactic": "Discovery",
        "recommendation": "Настроить сетевую сегментацию и мониторинг сканирований",
        "severity": "MEDIUM"
    },
    "T1071.001": {
        "name": "Web Protocols C2",
        "tactic": "Command and Control",
        "recommendation": "Настроить веб-прокси и проверку сертификатов",
        "severity": "HIGH"
    },
    "T1110.001": {
        "name": "Password Guessing",
        "tactic": "Credential Access",
        "recommendation": "Включить блокировку учётных записей и MFA",
        "severity": "MEDIUM"
    },
    "T1486": {
        "name": "Data Encrypted for Impact",
        "tactic": "Impact",
        "recommendation": "Настроить резервное копирование и изоляцию сети",
        "severity": "CRITICAL"
    },
    "T1566.001": {
        "name": "Spearphishing Attachment",
        "tactic": "Initial Access",
        "recommendation": "Включить сканирование вложений и обучение пользователей",
        "severity": "HIGH"
    },
    "T1547.001": {
        "name": "Registry Run Keys",
        "tactic": "Persistence",
        "recommendation": "Мониторить изменения в Run ключах реестра",
        "severity": "MEDIUM"
    },
    "T1048.003": {
        "name": "Exfiltration Over Unencrypted DNS",
        "tactic": "Exfiltration",
        "recommendation": "Настроить DNS фильтрацию и мониторинг TXT записей",
        "severity": "HIGH"
    }
}

# Нормальные процессы
NORMAL_PROCESSES = [
    "chrome.exe", "firefox.exe", "explorer.exe", "svchost.exe", 
    "outlook.exe", "teams.exe", "slack.exe", "code.exe", "notepad++.exe",
    "python.exe", "java.exe", "node.exe", "git.exe", "docker.exe"
]

# Подозрительные процессы
SUSPICIOUS_PROCESSES = [
    "powershell.exe", "cmd.exe", "wmic.exe", "rundll32.exe",
    "regsvr32.exe", "mshta.exe", "cscript.exe", "wscript.exe"
]

# Вредоносные индикаторы
MALICIOUS_INDICATORS = [
    ("powershell.exe", "-enc", "Base64 encoded command detected"),
    ("cmd.exe", "/c certutil", "Certificate tool abuse"),
    ("rundll32.exe", "javascript:", "Suspicious script execution"),
    ("wmic.exe", "process call create", "Remote process creation"),
    ("reg.exe", "add HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run", "Persistence via Registry"),
    ("net.exe", "user administrator /active:yes", "Privilege escalation attempt"),
    ("schtasks.exe", "/create /tn", "Scheduled task persistence"),
    ("bitsadmin.exe", "/transfer", "Download using BITS"),
    ("certutil.exe", "-urlcache", "Download using certutil"),
    ("nslookup.exe", "verylongsubdomain", "Potential DNS tunneling"),
]


def generate_normal_event() -> Dict[str, Any]:
    """Генерирует нормальное событие."""
    event_type = random.choice(["process", "network", "file", "registry", "auth"])
    
    if event_type == "process":
        return {
            "type": "process",
            "action": "start",
            "image": random.choice(NORMAL_PROCESSES),
            "pid": random.randint(1000, 50000),
            "parent_pid": random.randint(100, 5000),
            "command_line": None,
            "user": random.choice(["SYSTEM", "LOCAL SERVICE", "user"]),
            "timestamp": datetime.now().isoformat()
        }
    elif event_type == "network":
        return {
            "type": "network",
            "protocol": random.choice(["TCP", "UDP", "HTTP", "HTTPS", "DNS"]),
            "src_ip": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "dst_ip": random.choice(["8.8.8.8", "1.1.1.1", "142.250.185.46", "20.190.160.1"]),
            "src_port": random.randint(49152, 65535),
            "dst_port": random.choice([80, 443, 53, 8080, 3389]),
            "bytes_sent": random.randint(100, 50000),
            "bytes_received": random.randint(100, 100000),
            "timestamp": datetime.now().isoformat()
        }
    elif event_type == "file":
        paths = [
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "C:\\Users\\User\\Documents\\report.docx",
            "C:\\Users\\User\\Downloads\\setup.exe",
            "C:\\Windows\\Temp\\tmp1234.tmp",
            "C:\\Program Files\\App\\config.ini"
        ]
        return {
            "type": "file",
            "action": random.choice(["create", "read", "write", "delete", "rename"]),
            "path": random.choice(paths),
            "size": random.randint(0, 10485760),
            "timestamp": datetime.now().isoformat()
        }
    elif event_type == "registry":
        keys = [
            "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
            "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RecentDocs",
            "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters",
            "HKCU\\Control Panel\\Desktop"
        ]
        return {
            "type": "registry",
            "action": random.choice(["read", "write", "delete"]),
            "key": random.choice(keys),
            "value": f"Value_{random.randint(1, 100)}",
            "data": f"Data_{random.randint(1, 1000)}",
            "timestamp": datetime.now().isoformat()
        }
    else:
        users = ["alice", "bob", "charlie", "administrator", "guest"]
        return {
            "type": "auth",
            "user": random.choice(users),
            "result": "success" if random.random() < 0.95 else "failure",
            "source_ip": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "logon_type": random.choice([2, 3, 10]),
            "timestamp": datetime.now().isoformat()
        }


def generate_attack_event(severity: str = "MEDIUM") -> Dict[str, Any]:
    """Генерирует событие атаки."""
    technique_id = random.choice(list(ATTACK_TECHNIQUES.keys()))
    technique = ATTACK_TECHNIQUES[technique_id]
    
    indicator = random.choice(MALICIOUS_INDICATORS)
    
    return {
        "type": "process",
        "action": "start",
        "image": indicator[0],
        "command_line": f"{indicator[0]} {indicator[1]}",
        "pid": random.randint(50000, 99999),
        "parent_pid": random.randint(1000, 5000),
        "user": "SYSTEM",
        "mitre_technique": technique_id,
        "mitre_tactic": technique["tactic"],
        "severity": technique["severity"],
        "indicator": indicator[2],
        "recommendation": technique["recommendation"],
        "timestamp": datetime.now().isoformat()
    }


def generate_attack_chain() -> List[Dict[str, Any]]:
    """Генерирует цепочку атаки из 5-10 событий."""
    chain = []
    chain_length = random.randint(5, 12)
    
    techniques_used = []
    
    for i in range(chain_length):
        available = [t for t in ATTACK_TECHNIQUES.keys() if t not in techniques_used]
        if not available:
            available = list(ATTACK_TECHNIQUES.keys())
        
        technique_id = random.choice(available)
        techniques_used.append(technique_id)
        technique = ATTACK_TECHNIQUES[technique_id]
        
        indicator = random.choice(MALICIOUS_INDICATORS)
        
        event = {
            "type": random.choice(["process", "network", "file", "registry"]),
            "action": random.choice(["start", "create", "write", "connect", "modify"]),
            "image": indicator[0],
            "command_line": f"{indicator[0]} {indicator[1]}" if random.random() < 0.7 else None,
            "mitre_technique": technique_id,
            "mitre_tactic": technique["tactic"],
            "severity": technique["severity"],
            "indicator": indicator[2],
            "recommendation": technique["recommendation"],
            "timestamp": (datetime.now() - timedelta(seconds=random.randint(0, 300))).isoformat()
        }
        chain.append(event)
        
        for _ in range(random.randint(1, 3)):
            chain.append(generate_normal_event())
    
    return chain


def flatten_event(event: Dict[str, Any]) -> str:
    """Преобразует событие в строку для последовательности."""
    parts = [event.get('type', 'unknown')]
    
    if 'image' in event:
        parts.append(f"proc:{event['image']}")
    if 'protocol' in event:
        parts.append(f"proto:{event['protocol']}")
    if 'dst_port' in event:
        parts.append(f"port:{event['dst_port']}")
    if 'action' in event:
        parts.append(f"action:{event['action']}")
    if 'mitre_technique' in event:
        parts.append(f"mitre:{event['mitre_technique']}")
    if 'severity' in event:
        parts.append(f"sev:{event['severity']}")
    
    return "|".join(parts)


def generate_dataset(num_sequences: int, seq_len: int = 50) -> Tuple[List[List[str]], List[str]]:
    """
    Генерирует датасет для обучения.
    
    Returns:
        sequences: список последовательностей строк
        labels: список меток ('benign' или 'attack')
    """
    sequences = []
    labels = []
    
    for _ in range(num_sequences):
        is_attack = random.random() < 0.25
        
        if is_attack:
            attack_chain = generate_attack_chain()
            events = []
            for evt in attack_chain:
                events.append(flatten_event(evt))
            labels.append("attack")
        else:
            events = [flatten_event(generate_normal_event()) for _ in range(seq_len)]
            labels.append("benign")
        
        # Дополняем до нужной длины
        while len(events) < seq_len:
            events.append(flatten_event(generate_normal_event()))
        events = events[:seq_len]
        
        sequences.append(events)
    
    return sequences, labels


def generate_live_events(count: int = 10) -> List[Dict[str, Any]]:
    """Генерирует события для live-мониторинга."""
    events = []
    
    if random.random() < 0.2:
        events.append(generate_attack_event())
        for _ in range(random.randint(2, 5)):
            events.append(generate_normal_event())
            if random.random() < 0.3:
                events.append(generate_attack_event())
    else:
        for _ in range(count):
            events.append(generate_normal_event())
    
    return events
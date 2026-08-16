from app.services import job_market


def test_select_job_prefers_verified_detail_record(monkeypatch):
    monkeypatch.setattr(
        job_market,
        "load_verified_jobs",
        lambda: (
            {
                "source_type": "public_job_page",
                "review_status": "single_source_verified",
                "source_url": "https://example.test/java",
                "target_position": "Java 后端开发工程师",
                "category": "技术研发",
                "education": {"raw": "本科"},
                "experience": {"raw": "经验不限"},
                "must_skills": ["Java", "Spring Boot", "MySQL"],
                "nice_skills": [],
                "responsibilities": ["负责后端服务开发"],
            },
            {
                "source_type": "public_job_search_result",
                "review_status": "pending_manual_review",
                "source_url": "https://example.test/candidate",
                "target_position": "Java 实习生",
                "category": "技术研发",
                "must_skills": ["Java"],
            },
        ),
    )

    result = job_market.select_job_for_resume("本科生项目使用 Java、Spring Boot 和 MySQL", requested_position="Java")

    assert result["matched"] is True
    assert result["source_type"] == "public_job_page"
    assert result["source_url"].endswith("/java")
    assert result["fallback_used"] is False


def test_search_result_candidates_are_excluded_and_unknown_resume_uses_fallback(monkeypatch):
    monkeypatch.setattr(
        job_market,
        "load_verified_jobs",
        lambda: (
            {
                "source_type": "public_job_search_result",
                "review_status": "pending_manual_review",
                "source_url": "https://example.test/candidate",
                "target_position": "机器人岗位",
                "must_skills": ["机器人"],
            },
        ),
    )

    result = job_market.select_job_for_resume("中文写作、社团活动和志愿服务经历")

    assert result["matched"] is False
    assert result["fallback_used"] is True
    assert result["source_type"] == job_market.FALLBACK_LABEL


def test_match_exposes_evidence_and_requirement_alignment(monkeypatch):
    monkeypatch.setattr(
        job_market,
        "load_verified_jobs",
        lambda: ({
            "source_type": "public_job_page",
            "review_status": "single_source_verified",
            "source_url": "https://example.test/data",
            "target_position": "数据分析师",
            "category": "数据",
            "education": {"raw": "本科"},
            "experience": {"raw": "经验不限"},
            "must_skills": ["Python", "SQL"],
            "nice_skills": ["可视化"],
        },),
    )
    result = job_market.select_job_for_resume(
        "本科教育经历。技能：Python、SQL。项目：使用 Python 完成数据分析。",
        sections={"skills": ["Python", "SQL"], "projects": ["数据分析项目"]},
        requested_position="数据分析师",
    )
    assert result["matched"] is True
    assert result["evidence_coverage"] > 0
    assert result["match_explanation"]["must_coverage"] == 1.0
    assert result["match_explanation"]["education_alignment"] == "meets"


def test_no_target_only_recommends_related_jobs(monkeypatch):
    """未选手动岗位时不自动采用，只返回相关岗位推荐。"""
    monkeypatch.setattr(
        job_market,
        "load_verified_jobs",
        lambda: ({
            "id": "job-java-1",
            "source_type": "public_job_page",
            "review_status": "single_source_verified",
            "source_url": "https://example.test/java",
            "target_position": "Java 后端开发工程师",
            "category": "技术研发",
            "education": {"raw": "本科"},
            "experience": {"raw": "经验不限"},
            "must_skills": ["Java", "Spring Boot", "MySQL"],
            "nice_skills": [],
            "responsibilities": ["负责后端服务开发"],
        },),
    )
    result = job_market.select_job_for_resume(
        "本科生项目使用 Java、Spring Boot 和 MySQL",
        sections={"skills": ["Java", "Spring Boot", "MySQL"]},
        requested_position="",
    )
    assert result["matched"] is False
    assert result["recommendation_only"] is True
    assert result["adopted_as_target"] is False
    assert result["related_jobs"]
    assert result["related_jobs"][0]["target_position"] == "Java 后端开发工程师"
    assert result["related_jobs"][0]["id"] == "job-java-1"


def test_auto_match_rejects_generic_c_language_as_embedded(monkeypatch):
    """未选手动岗位时，仅命中「C语言」不应自动采用嵌入式开发实习生。"""
    monkeypatch.setattr(
        job_market,
        "load_verified_jobs",
        lambda: ({
            "source_type": "public_job_page",
            "review_status": "single_source_verified",
            "source_url": "https://example.test/embedded",
            "target_position": "嵌入式开发实习生",
            "category": "嵌入式开发",
            "education": {"raw": "大专"},
            "experience": {"raw": "在校/应届"},
            "must_skills": ["C语言"],
            "nice_skills": [],
            "responsibilities": ["设计和开发嵌入式系统的软件"],
        },),
    )
    result = job_market.select_job_for_resume(
        "本科 计算机。主修课程：C语言程序设计、高等数学。技能：Office、沟通能力。",
        sections={"education": ["主修 C语言"], "skills": ["Office"]},
        requested_position="",
    )
    assert result["matched"] is False
    assert result["fallback_used"] is True
    assert "嵌入式" not in (result.get("target_position") or "")


def test_public_job_payload_hides_skill_placeholder():
    payload = job_market.public_job_payload(
        {
            "id": "demo-1",
            "source_url": "https://example.test/sec",
            "source_type": "public_job_page",
            "review_status": "single_source_verified",
            "target_position": "网络安全工程师",
            "category": "网络安全",
            "company": "示例公司",
            "city": "西安",
            "education": {"raw": "大专"},
            "experience": {"raw": "经验不限"},
            "must_skills": ["岗位详情已核验，技能需人工复核"],
            "nice_skills": [],
            "responsibilities": [
                "岗位要求",
                "1、具备 Linux、Windows 系统知识；",
                "2、了解常见安全产品如防火墙、漏洞扫描；",
            ],
        }
    )
    assert "岗位详情已核验，技能需人工复核" not in payload["must_skills"]
    assert payload["must_skills"]
    assert "Linux" in payload["must_skills"] or any("防火墙" in item for item in payload["must_skills"])
    assert "岗位要求" not in payload["responsibilities"]


def test_rank_jobs_for_resume_returns_top5(monkeypatch):
    monkeypatch.setattr(
        job_market,
        "load_verified_jobs",
        lambda: (
            {
                "source_type": "public_job_page",
                "review_status": "single_source_verified",
                "source_url": "https://example.test/design",
                "target_position": "平面设计师",
                "category": "设计",
                "company": "设计公司",
                "city": "西安",
                "education": {"raw": "大专"},
                "experience": {"raw": "经验不限"},
                "must_skills": ["Photoshop", "Illustrator", "CorelDRAW"],
                "nice_skills": ["独立出图"],
                "responsibilities": ["完成广告物料设计"],
            },
            {
                "source_type": "public_job_page",
                "review_status": "single_source_verified",
                "source_url": "https://example.test/java",
                "target_position": "Java 后端",
                "category": "技术研发",
                "company": "研发公司",
                "city": "西安",
                "education": {"raw": "本科"},
                "experience": {"raw": "经验不限"},
                "must_skills": ["Java", "Spring", "MySQL"],
                "nice_skills": [],
                "responsibilities": ["负责后端开发"],
            },
            {
                "source_type": "public_job_page",
                "review_status": "single_source_verified",
                "source_url": "https://example.test/ops",
                "target_position": "新媒体运营",
                "category": "运营",
                "company": "运营公司",
                "city": "西安",
                "education": {"raw": "大专"},
                "experience": {"raw": "经验不限"},
                "must_skills": ["小红书", "剪映"],
                "nice_skills": [],
                "responsibilities": ["内容运营"],
            },
        ),
    )
    resume = "求职意向：平面设计师。技能 Photoshop、Illustrator、CorelDRAW。负责电商主图设计。"
    sections = {"skills": ["Photoshop", "Illustrator"], "projects": ["电商主图设计"]}
    ranked = job_market.rank_jobs_for_resume(resume, sections=sections, requested_position="平面设计师")
    selected = job_market.select_job_for_resume(resume, sections=sections, requested_position="平面设计师")
    assert ranked
    assert ranked[0]["target_position"] == "平面设计师"
    assert ranked[0]["match_percent"] >= ranked[-1]["match_percent"]
    assert selected["related_jobs"][0]["target_position"] == "平面设计师"
    basis = selected.get("requirement_basis") or {}
    assert basis.get("must_skills")
    assert "hit_count" in basis
    assert "miss_count" in basis

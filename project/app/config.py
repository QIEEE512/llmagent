from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    # 服务
    host: str = "0.0.0.0"
    port: int = 8080

    # 对外公开访问的后端基址（用于拼分享链接等）。
    # 例：https://api.example.com
    public_base_url: str | None = None

    # 安全
    jwt_secret: str = "dev-secret"  # 生产环境务必用环境变量覆盖
    jwt_algorithm: str = "HS256"
    access_token_expires_in: int = 7200

    # 数据库
    # 生产/联调建议通过环境变量 APP_MONGODB_URI 指定。
    # 为了匹配当前项目联调环境，这里给出默认连接串（仍可被环境变量覆盖）。
    mongodb_uri: str = "mongodb://root:50zm909rd59Elv9i@test-db-mongodb.ns-5g058qc1.svc:27017"
    mongodb_db: str = "digital_teacher"

    # 大模型（后续接入）
    # 支持 openai SDK（qwen3-max）和原 dashscope key（向后兼容）
    openai_api_key: str | None = None
    dashscope_api_key: str | None = None

    # OSS（用于生成公网可访问/签名 URL，供云端模型拉取素材）
    # 约定：私有桶 + 签名 URL（默认 10 分钟有效），bucket=agent-teacher-ai1，region=华东1（杭州）
    oss_endpoint: str = "https://oss-cn-hangzhou.aliyuncs.com"
    oss_bucket: str = "agent-teacher-ai1"
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
    # 可选：如果你绑定了自定义域名/CDN 域名，可配置在这里用于生成更短的 URL。
    # 注意：默认必须为 None，避免误用示例域名导致签名 URL 不可达。
    oss_public_base_url: str | None = None
    # 生成签名 URL 的有效期（秒）
    oss_presign_expires_in: int = 600


settings = Settings()

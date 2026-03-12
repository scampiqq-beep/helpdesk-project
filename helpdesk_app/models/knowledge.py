from .base import db, utcnow

class KnowledgeBaseCategory(db.Model):
    __tablename__ = 'kb_categories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), unique=True, nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    articles = db.relationship('KnowledgeBaseArticle', back_populates='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<KBCategory {self.title}>"


class KnowledgeBaseArticle(db.Model):
    __tablename__ = 'kb_articles'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('kb_categories.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)  # краткий шаблон для вставки в комментарий
    body = db.Column(db.Text, nullable=True)      # полная статья
    tags = db.Column(db.String(400), nullable=True)  # comma-separated
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    category = db.relationship('KnowledgeBaseCategory', back_populates='articles')

    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def __repr__(self):
        return f"<KBArticle {self.id}:{self.title}>"


class KnowledgeBaseFavorite(db.Model):
    """Избранное статей для операторов и клиентов.

    user_type: 'op' | 'user'
    user_id: id из users
    """
    __tablename__ = 'kb_favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(10), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey('kb_articles.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    article = db.relationship('KnowledgeBaseArticle')

    __table_args__ = (
        db.UniqueConstraint('user_type', 'user_id', 'article_id', name='uq_kb_fav_user_article'),
    )

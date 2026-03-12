from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from helpdesk_app.models.base import db
from helpdesk_app.models.knowledge import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    KnowledgeBaseFavorite,
)
from helpdesk_app.models.reference import FAQ
from helpdesk_app.services.admin_service import AdminService


class KnowledgeService:
    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @staticmethod
    def _kb_user_key(user):
        try:
            if getattr(user, 'role', None) == 'client':
                return ('user', int(user.id))
        except Exception:
            pass
        return ('op', int(user.id))

    @classmethod
    def _is_admin(cls) -> bool:
        return getattr(current_user, 'role', '') == 'admin'

    @classmethod
    def _is_operator(cls) -> bool:
        try:
            return bool(current_user.is_operator())
        except Exception:
            return getattr(current_user, 'role', '') in {'admin', 'operator'}

    @classmethod
    def render_index(cls):
        q = (request.args.get('q') or '').strip()
        only_fav = request.args.get('fav') == '1'
        user_type, user_id = cls._kb_user_key(current_user)

        fav_ids = set()
        try:
            fav_ids = {
                x.article_id
                for x in KnowledgeBaseFavorite.query.filter_by(user_type=user_type, user_id=user_id).all()
            }
        except Exception:
            fav_ids = set()

        categories = (
            KnowledgeBaseCategory.query
            .filter_by(is_active=True)
            .order_by(KnowledgeBaseCategory.sort_order.asc(), KnowledgeBaseCategory.title.asc())
            .all()
        )

        art_q = KnowledgeBaseArticle.query.filter_by(is_published=True)
        if q:
            like = f'%{q}%'
            art_q = art_q.filter(or_(
                KnowledgeBaseArticle.title.ilike(like),
                KnowledgeBaseArticle.tags.ilike(like),
                KnowledgeBaseArticle.summary.ilike(like),
                KnowledgeBaseArticle.body.ilike(like),
            ))
        if only_fav:
            art_q = art_q.filter(KnowledgeBaseArticle.id.in_(list(fav_ids))) if fav_ids else art_q.filter(KnowledgeBaseArticle.id == -1)

        articles = art_q.order_by(KnowledgeBaseArticle.updated_at.desc(), KnowledgeBaseArticle.id.desc()).all()
        by_cat: dict[int, list] = {}
        for article in articles:
            by_cat.setdefault(article.category_id or 0, []).append(article)

        return render_template(
            'knowledge/index.html',
            q=q,
            only_fav=only_fav,
            categories=categories,
            by_cat=by_cat,
            fav_ids=fav_ids,
            is_operator=cls._is_operator(),
            is_admin=cls._is_admin(),
        )

    @classmethod
    def render_article(cls, article_id: int):
        article = KnowledgeBaseArticle.query.get_or_404(article_id)
        if not article.is_published and not cls._is_admin():
            abort(404)
        user_type, user_id = cls._kb_user_key(current_user)
        is_fav = KnowledgeBaseFavorite.query.filter_by(
            user_type=user_type, user_id=user_id, article_id=article.id
        ).first() is not None
        return render_template(
            'knowledge/article.html',
            article=article,
            is_favorite=is_fav,
            is_operator=cls._is_operator(),
            is_admin=cls._is_admin(),
        )

    @classmethod
    def render_manage(cls):
        AdminService.ensure_admin()
        categories = (
            KnowledgeBaseCategory.query
            .order_by(KnowledgeBaseCategory.sort_order.asc(), KnowledgeBaseCategory.title.asc())
            .all()
        )
        articles = (
            KnowledgeBaseArticle.query
            .order_by(KnowledgeBaseArticle.updated_at.desc(), KnowledgeBaseArticle.id.desc())
            .all()
        )
        return render_template('knowledge/manage.html', categories=categories, articles=articles)

    @classmethod
    def render_faq_form(cls, mode: str, faq=None):
        return render_template('faq_form.html', mode=mode, faq=faq)

    @classmethod
    def add_faq(cls):
        AdminService.ensure_admin()
        if request.method == 'POST':
            question = (request.form.get('question') or '').strip()
            answer = (request.form.get('answer') or '').strip()
            category = (request.form.get('category') or 'Общее').strip() or 'Общее'
            order_raw = (request.form.get('order') or '0').strip()
            order = int(order_raw) if order_raw.lstrip('-').isdigit() else 0
            is_active = request.form.get('is_active') in ('1', 'on', 'true', 'yes')
            if not question or not answer:
                flash('Заполните вопрос и ответ', 'error')
                return cls.render_faq_form('add')
            faq = FAQ(question=question, answer=answer, category=category, order=order, is_active=is_active)
            db.session.add(faq)
            db.session.commit()
            flash('Статья добавлена', 'success')
            return redirect(url_for('knowledge'))
        return cls.render_faq_form('add')

    @classmethod
    def edit_faq(cls, faq_id: int):
        AdminService.ensure_admin()
        faq = FAQ.query.get_or_404(faq_id)
        if request.method == 'POST':
            faq.question = (request.form.get('question') or '').strip()
            faq.answer = (request.form.get('answer') or '').strip()
            faq.category = (request.form.get('category') or 'Общее').strip() or 'Общее'
            order_raw = (request.form.get('order') or '0').strip()
            faq.order = int(order_raw) if order_raw.lstrip('-').isdigit() else 0
            faq.is_active = request.form.get('is_active') in ('1', 'on', 'true', 'yes')
            if not faq.question or not faq.answer:
                flash('Заполните вопрос и ответ', 'error')
                return cls.render_faq_form('edit', faq=faq)
            db.session.commit()
            flash('Изменения сохранены', 'success')
            return redirect(url_for('knowledge'))
        return cls.render_faq_form('edit', faq=faq)

    @classmethod
    def api_templates(cls):
        q = (request.args.get('q') or '').strip()
        only_fav = request.args.get('fav') == '1'
        limit = min(int(request.args.get('limit') or 50), 100)
        user_type, user_id = cls._kb_user_key(current_user)
        fav_ids = {
            x.article_id for x in KnowledgeBaseFavorite.query.filter_by(user_type=user_type, user_id=user_id).all()
        }
        qs = KnowledgeBaseArticle.query.filter_by(is_published=True)
        if q:
            like = f'%{q}%'
            qs = qs.filter(or_(
                KnowledgeBaseArticle.title.ilike(like),
                KnowledgeBaseArticle.tags.ilike(like),
                KnowledgeBaseArticle.summary.ilike(like),
            ))
        if only_fav:
            qs = qs.filter(KnowledgeBaseArticle.id.in_(list(fav_ids))) if fav_ids else qs.filter(KnowledgeBaseArticle.id == -1)
        rows = qs.order_by(KnowledgeBaseArticle.updated_at.desc(), KnowledgeBaseArticle.id.desc()).limit(limit).all()
        return jsonify({
            'success': True,
            'items': [{
                'id': a.id,
                'title': a.title,
                'category': a.category.title if a.category else '',
                'summary': a.summary or '',
                'url': url_for('kb_article', article_id=a.id),
                'is_favorite': a.id in fav_ids,
            } for a in rows]
        })

    @classmethod
    def toggle_favorite(cls, article_id: int):
        KnowledgeBaseArticle.query.get_or_404(article_id)
        user_type, user_id = cls._kb_user_key(current_user)
        fav = KnowledgeBaseFavorite.query.filter_by(
            user_type=user_type,
            user_id=user_id,
            article_id=article_id,
        ).first()
        if fav:
            db.session.delete(fav)
            db.session.commit()
            return jsonify({'success': True, 'is_favorite': False})
        db.session.add(KnowledgeBaseFavorite(user_type=user_type, user_id=user_id, article_id=article_id))
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': True})

    @classmethod
    def _categories(cls):
        return KnowledgeBaseCategory.query.order_by(
            KnowledgeBaseCategory.sort_order.asc(),
            KnowledgeBaseCategory.title.asc(),
        ).all()

    @classmethod
    def add_category(cls):
        AdminService.ensure_admin()
        if request.method == 'POST':
            title = (request.form.get('title') or '').strip()
            sort_raw = (request.form.get('sort_order') or '0').strip()
            sort_order = int(sort_raw) if sort_raw.lstrip('-').isdigit() else 0
            is_active = request.form.get('is_active') in ('1', 'on', 'true', 'yes')
            if not title:
                flash('Введите название категории', 'warning')
                return render_template('knowledge/category_form.html', mode='add', category=None)
            db.session.add(KnowledgeBaseCategory(title=title, sort_order=sort_order, is_active=is_active))
            db.session.commit()
            flash('Категория добавлена', 'success')
            return redirect(url_for('kb_manage'))
        return render_template('knowledge/category_form.html', mode='add', category=None)

    @classmethod
    def edit_category(cls, category_id: int):
        AdminService.ensure_admin()
        category = KnowledgeBaseCategory.query.get_or_404(category_id)
        if request.method == 'POST':
            category.title = (request.form.get('title') or '').strip()
            sort_raw = (request.form.get('sort_order') or '0').strip()
            category.sort_order = int(sort_raw) if sort_raw.lstrip('-').isdigit() else 0
            category.is_active = request.form.get('is_active') in ('1', 'on', 'true', 'yes')
            if not category.title:
                flash('Введите название категории', 'warning')
                return render_template('knowledge/category_form.html', mode='edit', category=category)
            db.session.commit()
            flash('Категория сохранена', 'success')
            return redirect(url_for('kb_manage'))
        return render_template('knowledge/category_form.html', mode='edit', category=category)

    @classmethod
    def delete_category(cls, category_id: int):
        AdminService.ensure_admin()
        category = KnowledgeBaseCategory.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        flash('Категория удалена', 'success')
        return redirect(url_for('kb_manage'))

    @classmethod
    def add_article(cls):
        AdminService.ensure_admin()
        categories = cls._categories()
        if request.method == 'POST':
            title = (request.form.get('title') or '').strip()
            summary = (request.form.get('summary') or '').strip()
            body = (request.form.get('body') or '').strip()
            tags = (request.form.get('tags') or '').strip()
            category_id = request.form.get('category_id')
            is_published = request.form.get('is_published') in ('1', 'on', 'true', 'yes')
            if not title or not summary:
                flash('Заполните название и краткий шаблон', 'warning')
                return render_template('knowledge/article_form.html', mode='add', article=None, categories=categories)
            cid = int(category_id) if category_id and category_id.isdigit() else None
            article = KnowledgeBaseArticle(
                title=title,
                summary=summary,
                body=body,
                tags=tags,
                category_id=cid,
                is_published=is_published,
            )
            db.session.add(article)
            db.session.commit()
            flash('Статья добавлена', 'success')
            return redirect(url_for('kb_manage'))
        return render_template('knowledge/article_form.html', mode='add', article=None, categories=categories)

    @classmethod
    def edit_article(cls, article_id: int):
        AdminService.ensure_admin()
        article = KnowledgeBaseArticle.query.get_or_404(article_id)
        categories = cls._categories()
        if request.method == 'POST':
            article.title = (request.form.get('title') or '').strip()
            article.summary = (request.form.get('summary') or '').strip()
            article.body = (request.form.get('body') or '').strip()
            article.tags = (request.form.get('tags') or '').strip()
            category_id = request.form.get('category_id')
            article.category_id = int(category_id) if category_id and category_id.isdigit() else None
            article.is_published = request.form.get('is_published') in ('1', 'on', 'true', 'yes')
            if not article.title or not article.summary:
                flash('Заполните название и краткий шаблон', 'warning')
                return render_template('knowledge/article_form.html', mode='edit', article=article, categories=categories)
            db.session.commit()
            flash('Статья сохранена', 'success')
            return redirect(url_for('kb_manage'))
        return render_template('knowledge/article_form.html', mode='edit', article=article, categories=categories)

    @classmethod
    def delete_article(cls, article_id: int):
        AdminService.ensure_admin()
        article = KnowledgeBaseArticle.query.get_or_404(article_id)
        db.session.delete(article)
        db.session.commit()
        flash('Статья удалена', 'success')
        return redirect(url_for('kb_manage'))

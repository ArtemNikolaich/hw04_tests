from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from ..models import Group, Post

from http import HTTPStatus

User = get_user_model()


class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            group=cls.group,
        )

    def setUp(self):
        # Создаём неавторизованный клиент
        self.guest_client = Client()
        # Создаём авторизованный клиент
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_of_post = User.objects.create_user(
            username='author_of_post'
        )
        self.authorized_client_of_post = Client()
        self.authorized_client_of_post.force_login(self.author_of_post)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test'}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'StasBasov'}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                if reverse_name == reverse('posts:post_edit',
                                           kwargs={'post_id': self.post.id}):
                    response = self.authorized_client_of_post.get(reverse_name)
                else:
                    response = self.authorized_client.get(reverse_name)
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                    self.assertTemplateUsed(response, template,)

    def test_index_view_context(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Это главная страница проекта Yatube')
        self.assertContains(response, 'Тестовый текст')
        self.assertIn('page_obj', response.context)
        self.assertIn('posts', response.context)

    def test_group_posts_view_context(self):
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': 'test'}))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Тестовая группа')
        self.assertContains(response, 'Тестовый текст')
        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)
        self.assertIn('posts', response.context)

    def test_profile_view_context(self):
        response = self.client.get(reverse('posts:profile',
                                           kwargs={'username': 'auth'}))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Профайл пользователя auth')
        self.assertContains(response, 'Тестовый текст')
        self.assertIn('page_obj', response.context)
        self.assertIn('author', response.context)
        self.assertIn('total_posts', response.context)

    def test_post_detail_view_context(self):
        response = self.client.get(reverse('posts:post_detail',
                                           kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Тестовый текст')
        self.assertIn('post', response.context)

    def test_create_post_form(self):
        url = reverse('posts:post_create')
        response = self.authorized_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'posts/create_post.html')
        self.assertIsInstance(response.context['form'], forms.ModelForm)
        self.assertFalse('post' in response.context)

    def test_edit_post_form(self):
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        response = self.authorized_client.get(url)
        self.assertRedirects(response, reverse('posts:post_detail',
                                               kwargs={'post_id': self.post.id}
                                               ))

    def test_create_post_in_group(self):
        """Если при создании поста указать группу, то этот пост появляется
        на главной странице сайта, на странице выбранной группы и в профайле
        пользователя."""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new_group',
            description='Новое описание',
        )
        post_data = {
            'text': 'Текст нового поста',
            'group': new_group.pk,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=post_data,
            follow=True
        )

        # Проверяем наличие поста на главной странице,
        # странице выбранной группы
        # и в профиле автора
        pages_to_check = {
            reverse('posts:index'): post_data['text'],
            reverse('posts:group_list', kwargs={'slug': new_group.slug}):
            post_data['text'],
            reverse('posts:profile', kwargs={'username': self.user.username}):
            post_data['text']
        }
        for page, text in pages_to_check.items():
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertContains(response, text)

    def test_create_post_in_wrong_group(self):
        """Пост не должен попадать в группу,
        для которой не был предназначен."""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new_group',
            description='Новое описание',
        )
        post_data = {
            'text': 'Текст нового поста',
            'group': new_group.pk,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=post_data,
            follow=True
        )

        # Проверяем отсутствие поста на странице выбранной группы
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertNotContains(response, post_data['text'])

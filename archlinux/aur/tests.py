from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.template import Template, Context
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files import File
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage as storage

from aur.forms import PackageSearchForm, PackageSubmitForm
from aur.models import Package, PackageNotification, Repository, PackageFile

class AurTestCase(TestCase):
    fixtures = ['test/users', 'test/packages']


class AurViewTests(AurTestCase):
    def test_index_view(self):
        response = self.client.get(reverse('aur-main'))
        self.assertEqual(response.status_code, 200)

    def test_search_view(self):
        response = self.client.get(reverse('aur-search'))
        self.assertEqual(response.status_code, 200)

        # Results with only one hit should redirect to package immediately
        response = self.client.get(reverse('aur-search'), data={
            'query': 'unique',
        })
        self.assertRedirects(response, reverse('aur-package_detail', kwargs={
            'slug': 'unique_package',
        }))

    def test_submit_view(self):
        self.client.login(username='normal_user', password='normal_user')
        response = self.client.get(reverse('aur-submit_package'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_package_view(self):
        response = self.client.get(reverse('aur-package_detail', kwargs={
            'slug': 'unique_package',
        }))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('aur-package_detail', kwargs={
            'slug': 'DoesNotExist',
        }))
        self.assertEqual(response.status_code, 404)


class AurAPITests(AurTestCase):
    def test_search_view(self):
        response = self.client.get(reverse('aur.views.api_search', kwargs={
            'query': 'package',
            'format': 'json',
        }))
        self.assertEqual(response.status_code, 200)

    def test_package_view(self):
        response = self.client.get(reverse('aur.views.api_package_info', kwargs={
            'object_id' :'unique_package',
            'format': 'json',
        }))
        self.assertEqual(response.status_code, 200)

        # Requested package does not exist (404)
        response = self.client.get(reverse('aur.views.api_package_info', kwargs={
            'object_id' :'DoesNotExist',
            'format': 'json',
        }))
        self.assertEqual(response.status_code, 404)


class AurModelTests(AurTestCase):
    def test_update_notification(self):
        user = User.objects.get(username='normal_user')
        package = Package.objects.get(name='unique_package')
        PackageNotification(package=package, user=user).save()
        # Update version and save
        package.version = unicode(float(package.version) + 1)
        package.save()
        # Check that the mail was sent out
        self.assertEquals(len(mail.outbox), 1)

    def test_delete_notification(self):
        user = User.objects.get(username='normal_user')
        package = Package.objects.get(name='unique_package')
        PackageNotification(package=package, user=user).save()
        package.delete()
        # Check that the mail was sent out
        # FIXME: This currently fails because tarball doesn't actually exist,
        # and its removal is attempted
        self.assertEquals(len(mail.outbox), 1)


class AurSearchFormTests(AurTestCase):
    def test_search_form(self):
        form = PackageSearchForm(data={
            'query': 'unique_package'
        })
        self.failUnless(form.is_valid())
        results = form.search()
        self.assertEquals(results.count(), 1)
        self.assertEquals(results[0].name, 'unique_package')


class AurSubmitFormTests(AurTestCase):
    def setUp(self):
        self.fileobj = SimpleUploadedFile('PKGBUILD', """
            pkgname="new_package"
            pkgver=1.0
            pkgrel=1
            pkgdesc="test pkgbuild"
            arch=(i686)
            license=("MIT")
            md5sums=()
            source=()
            build() {
            }
        """.strip())
        self.repository = Repository.objects.all()[0].name.lower()
        self.form = PackageSubmitForm(
            {'repository': self.repository},
            {'package': self.fileobj}
        )
        self.user = authenticate(username="normal_user", password="normal_user")

    def tearDown(self):
        self.fileobj.close()

    def test_validate_sane(self):
        self.assertTrue(self.form.is_valid(), "valid package did not validate:\n%r" % self.form.errors)

    def test_save_plain(self):
        self.form.save(self.user)
        package = None
        try:
            package = Package.objects.get(name="new_package")
        except Package.DoesNotExist:
            self.fail("package was not saved to the database")
        self.assertTrue(storage.exists(package.tarball.path))
        found = False
        # FIXME: This is stupid
        for f in PackageFile.objects.filter(package=package):
            if f.filename and f.filename.name.find("PKGBUILD") >= 0:
                found = True
                self.assertTrue(storage.exists(f.filename.path))
        self.assertTrue(found, "PKGBUILD was not uploaded")
        self.assertTrue(storage.exists(package.tarball.path))

    def test_save_tarball(self):
        import tempfile
        import tarfile
        import os
        tarfileobj = tarfile.open(os.path.join(tempfile.mkdtemp(), "new_package.tar"), "w")
        path = os.path.join(tempfile.mkdtemp(), "PKGBUILD")
        fp = open(path, "w")
        fp.writelines(self.fileobj.readlines())
        fp.close()
        tarfileobj.add(path, "PKGBUILD")
        self.form.save(self.user)
        package = None
        try:
            package = Package.objects.get(name="new_package")
        except Package.DoesNotExist:
            self.fail("package was not saved to the database")
        self.assertTrue(storage.exists(package.tarball.path))


class AurTemplateTagTests(AurTestCase):
    def test_has_update_notification(self):
        user = User.objects.get(username='normal_user')
        package = Package.objects.get(name='unique_package')
        context = Context({
            'user': user,
            'package': package,
        })
        template = Template("""
            {% load aur_tags %}
            {% if user|has_update_notification:package %}
                True
            {% else %}
                False
            {% endif %}
        """)
        self.assertEquals(template.render(context).strip(), "False")
        PackageNotification(package=package, user=user).save()
        self.assertEquals(template.render(context).strip(), "True")


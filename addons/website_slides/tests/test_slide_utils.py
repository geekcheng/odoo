# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common as slides_common
from odoo.tests.common import users


class TestSlidesManagement(slides_common.SlidesCase):

    @users('user_officer')
    def test_get_categorized_slides(self):
        new_category = self.env['slide.slide'].create({
            'name': 'Cooking Tips for Cooking Humans',
            'channel_id': self.channel.id,
            'is_category': True,
            'sequence': 5,
        })
        order = self.env['slide.slide']._order_by_strategy['sequence']
        categorized_slides = self.channel._get_categorized_slides([], order)
        self.assertEqual(categorized_slides[0]['category'], False)
        self.assertEqual(categorized_slides[1]['category'], self.category)
        self.assertEqual(categorized_slides[1]['total_slides'], 2)
        self.assertEqual(categorized_slides[2]['total_slides'], 0)
        self.assertEqual(categorized_slides[2]['category'], new_category)

    @users('user_manager')
    def test_archive(self):
        self.env['slide.slide.partner'].create({
            'slide_id': self.slide.id,
            'channel_id': self.channel.id,
            'partner_id': self.user_manager.partner_id.id,
            'completed': True
        })
        channel_partner = self.channel._action_add_members(self.user_manager.partner_id)

        self.assertTrue(self.channel.active)
        self.assertTrue(self.channel.is_published)
        self.assertFalse(channel_partner.completed)
        for slide in self.channel.slide_ids:
            self.assertTrue(slide.active, "All slide should be archived when a channel is archived")
            self.assertTrue(slide.is_published, "All slide should be unpublished when a channel is archived")

        self.channel.toggle_active()
        self.assertFalse(self.channel.active)
        self.assertFalse(self.channel.is_published)
        # channel_partner should still NOT be marked as completed
        self.assertFalse(channel_partner.completed)

        for slide in self.channel.slide_ids:
            self.assertFalse(slide.active, "All slides should be archived when a channel is archived")
            if not slide.is_category:
                self.assertFalse(slide.is_published, "All slides should be unpublished when a channel is archived, except categories")
            else:
                self.assertTrue(slide.is_published, "All slides should be unpublished when a channel is archived, except categories")

    def test_mail_completed(self):
        """ When the slide.channel is completed, an email is supposed to be sent to people that completed it. """
        channel_2 = self.env['slide.channel'].create({
            'name': 'Test Course 2',
            'slide_ids': [(0, 0, {
                'name': 'Test Slide 1'
            })]
        })
        all_users = self.user_officer | self.user_emp | self.user_portal
        all_channels = self.channel | channel_2
        all_channels.sudo()._action_add_members(all_users.partner_id)
        slide_slide_vals = []
        for slide in all_channels.slide_content_ids:
            for user in self.user_officer | self.user_emp:
                slide_slide_vals.append({
                    'slide_id': slide.id,
                    'channel_id': self.channel.id,
                    'partner_id': user.partner_id.id,
                    'completed': True
                })
        self.env['slide.slide.partner'].create(slide_slide_vals)
        created_mails = self.env['mail.mail'].search([])

        # 2 'congratulations' emails are supposed to be sent to user_officer and user_emp
        for user in self.user_officer | self.user_emp:
            self.assertTrue(
                any(mail.model == 'slide.channel.partner' and user.partner_id in mail.recipient_ids
                    for mail in created_mails)
            )
        # user_portal has not finished the course, it should not receive anything
        self.assertFalse(
            any(mail.model == 'slide.channel.partner' and self.user_portal.partner_id in mail.recipient_ids
                for mail in created_mails)
        )


class TestSequencing(slides_common.SlidesCase):

    @users('user_officer')
    def test_category_update(self):
        self.assertEqual(self.channel.slide_category_ids, self.category)
        self.assertEqual(self.channel.slide_content_ids, self.slide | self.slide_2 | self.slide_3)
        self.assertEqual(self.slide.category_id, self.env['slide.slide'])
        self.assertEqual(self.slide_2.category_id, self.category)
        self.assertEqual(self.slide_3.category_id, self.category)
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.category.id, self.slide_2.id, self.slide_3.id])

        self.slide.write({'sequence': 0})
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.category.id, self.slide_2.id, self.slide_3.id])
        self.assertEqual(self.slide_2.category_id, self.category)
        self.slide_2.write({'sequence': 1})
        self.channel.invalidate_cache()
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_2.id, self.category.id, self.slide_3.id])
        self.assertEqual(self.slide_2.category_id, self.env['slide.slide'])

        channel_2 = self.env['slide.channel'].create({
            'name': 'Test2'
        })
        new_category = self.env['slide.slide'].create({
            'name': 'NewCategorySlide',
            'channel_id': channel_2.id,
            'is_category': True,
            'sequence': 1,
        })
        new_category_2 = self.env['slide.slide'].create({
            'name': 'NewCategorySlide2',
            'channel_id': channel_2.id,
            'is_category': True,
            'sequence': 2,
        })
        new_slide = self.env['slide.slide'].create({
            'name': 'NewTestSlide',
            'channel_id': channel_2.id,
            'sequence': 2,
        })
        self.assertEqual(new_slide.category_id, new_category_2)
        (new_slide | self.slide_3).write({'sequence': 1})
        self.assertEqual(new_slide.category_id, new_category)
        self.assertEqual(self.slide_3.category_id, self.env['slide.slide'])

        (new_slide | self.slide_3).write({'sequence': 0})
        self.assertEqual(new_slide.category_id, self.env['slide.slide'])
        self.assertEqual(self.slide_3.category_id, self.env['slide.slide'])

    @users('user_officer')
    def test_resequence(self):
        self.assertEqual(self.slide.sequence, 1)
        self.category.write({'sequence': 4})
        self.slide_2.write({'sequence': 8})
        self.slide_3.write({'sequence': 3})

        self.channel.invalidate_cache()
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_3.id, self.category.id, self.slide_2.id])
        self.assertEqual(self.slide.sequence, 1)

        # insert a new category and check resequence_slides does as expected
        new_category = self.env['slide.slide'].create({
            'name': 'Sub-cooking Tips Category',
            'channel_id': self.channel.id,
            'is_category': True,
            'is_published': True,
            'sequence': 2,
        })
        new_category.flush()
        self.channel.invalidate_cache()
        self.channel._resequence_slides(self.slide_3, force_category=new_category)
        self.assertEqual(self.slide.sequence, 1)
        self.assertEqual(new_category.sequence, 2)
        self.assertEqual(self.slide_3.sequence, 3)
        self.assertEqual(self.category.sequence, 4)
        self.assertEqual(self.slide_2.sequence, 5)
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, new_category.id, self.slide_3.id, self.category.id, self.slide_2.id])


class TestFromURL(slides_common.SlidesCase):
    def test_video_youtube(self):
        youtube_urls = {
            'W0JQcpGLSFw': [
                'https://youtu.be/W0JQcpGLSFw',
                'https://www.youtube.com/watch?v=W0JQcpGLSFw',
                'https://www.youtube.com/watch?v=W0JQcpGLSFw&list=PL1-aSABtP6ACZuppkBqXFgzpNb2nVctZx',
            ],
            'vmhB-pt7EfA': [  # id starts with v, it is important
                'https://youtu.be/vmhB-pt7EfA',
                'https://www.youtube.com/watch?feature=youtu.be&v=vmhB-pt7EfA',
                'https://www.youtube.com/watch?v=vmhB-pt7EfA&list=PL1-aSABtP6ACZuppkBqXFgzpNb2nVctZx&index=7',
            ],
            'hlhLv0GN1hA': [
                'https://www.youtube.com/v/hlhLv0GN1hA',
                'https://www.youtube.com/embed/hlhLv0GN1hA',
                'https://www.youtube-nocookie.com/embed/hlhLv0GN1hA',
                'https://m.youtube.com/watch?v=hlhLv0GN1hA',
            ],
        }

        Slide = self.env['slide.slide'].with_context(website_slides_skip_fetch_metadata=True)

        # test various YouTube URL formats
        for youtube_id, urls in youtube_urls.items():
            for url in urls:
                with self.subTest(url=url, id=youtube_id):
                    slide = Slide.create({
                        'name': 'dummy',
                        'channel_id': self.channel.id,
                        'url': url,
                        'slide_category': 'video'
                    })
                    self.assertEqual('youtube', slide.video_source_type)
                    self.assertEqual(youtube_id, slide.youtube_id)

    def test_video_google_drive(self):
        google_drive_urls = {
            '1qU5nHVNbz_r84P_IS5kDzoCuC1h5ZAZR': [
                'https://drive.google.com/file/d/1qU5nHVNbz_r84P_IS5kDzoCuC1h5ZAZR/view?usp=sharing',
                'https://drive.google.com/file/d/1qU5nHVNbz_r84P_IS5kDzoCuC1h5ZAZR',
            ],
        }

        Slide = self.env['slide.slide'].with_context(website_slides_skip_fetch_metadata=True)

        # test various Google Drive URL formats
        for google_drive_id, urls in google_drive_urls.items():
            for url in urls:
                with self.subTest(url=url, id=google_drive_id):
                    slide = Slide.create({
                        'name': 'dummy',
                        'channel_id': self.channel.id,
                        'url': url,
                        'slide_category': 'video'
                    })
                    self.assertEqual('google_drive', slide.video_source_type)
                    self.assertEqual(google_drive_id, slide.google_drive_id)

    def test_video_vimeo(self):
        vimeo_urls = {
            # regular URL from Vimeo
            '545859999': [
                'https://vimeo.com/545859999',
                'https://vimeo.com/545859999?autoplay=1',
            ],
            # test channel URL from Vimeo
            '551979139': [
                'https://vimeo.com/channels/staffpicks/551979139',
                'https://vimeo.com/channels/staffpicks/551979139?autoplay=1',
            ],
            # test URL from Vimeo with setting 'with URL only'
            # we need to store both the ID and the token, see '_compute_embed_code' method for details
            '545859999/94dd03ddb0': [
                'https://vimeo.com/545859999/94dd03ddb0',
                'https://vimeo.com/545859999/94dd03ddb0?autoplay=1',
            ],
        }

        Slide = self.env['slide.slide'].with_context(website_slides_skip_fetch_metadata=True)

        # test various Vimeo URL formats
        for vimeo_id, urls in vimeo_urls.items():
            for url in urls:
                with self.subTest(url=url, id=vimeo_id):
                    slide = Slide.create({
                        'name': 'dummy',
                        'channel_id': self.channel.id,
                        'url': url,
                        'slide_category': 'video'
                    })
                    self.assertEqual('vimeo', slide.video_source_type)
                    self.assertEqual(vimeo_id, slide.vimeo_id)

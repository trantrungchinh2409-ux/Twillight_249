import json
import unittest
from jat_design.compare_mentions import features


class FeatureTests(unittest.TestCase):
    def test_comparison_exposes_features_not_content_or_ids(self):
        event = {'message': {'text': '@Bot JAT Design private-content <@private-bot-id>',
                             'chat': {'id': 'private-group-id'},
                             'from': {'id': 'private-user-id', 'is_bot': False}}}
        result = features(event, 'private-bot-id')
        self.assertTrue(result['contains_bot_display_text'])
        self.assertTrue(result['contains_bot_id_in_text'])
        self.assertTrue(result['has_angle_at_markup'])
        self.assertNotIn('private-', json.dumps(result))

    def test_text_name_is_not_claimed_to_be_verified_mention(self):
        result = features({'message': {'text': '@Bot JAT Design typed manually'}}, 'bot-id')
        self.assertTrue(result['contains_bot_display_text'])
        self.assertNotIn('mention_verified', result)
        self.assertFalse(result['contains_bot_id_in_text'])

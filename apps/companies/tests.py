"""
Tests for Team Seats feature in companies app.
"""
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from apps.accounts.models import CustomUser
from apps.companies.models import Company, TeamMember, TeamInvitation


class TeamMemberModelTests(TestCase):
    """Tests for TeamMember model."""

    def setUp(self):
        """Set up test data."""
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.member_user = CustomUser.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            user=self.owner,
            owner=self.owner,
            name='Test Company'
        )

    def test_create_team_member(self):
        """Test creating a team member."""
        member = TeamMember.objects.create(
            company=self.company,
            user=self.member_user,
            role='member',
            invited_by=self.owner
        )
        self.assertEqual(member.company, self.company)
        self.assertEqual(member.user, self.member_user)
        self.assertEqual(member.role, 'member')
        self.assertIsNotNone(member.joined_at)

    def test_team_member_roles(self):
        """Test team member role choices."""
        admin_member = TeamMember.objects.create(
            company=self.company,
            user=self.member_user,
            role='admin'
        )
        self.assertEqual(admin_member.get_role_display(), 'Admin')

    def test_unique_together_constraint(self):
        """Test that a user can only be a member of a company once."""
        TeamMember.objects.create(
            company=self.company,
            user=self.member_user,
            role='member'
        )
        with self.assertRaises(Exception):
            TeamMember.objects.create(
                company=self.company,
                user=self.member_user,
                role='admin'
            )


class TeamInvitationModelTests(TestCase):
    """Tests for TeamInvitation model."""

    def setUp(self):
        """Set up test data."""
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.company = Company.objects.create(
            user=self.owner,
            owner=self.owner,
            name='Test Company'
        )

    def test_create_invitation(self):
        """Test creating an invitation."""
        invitation = TeamInvitation.objects.create(
            company=self.company,
            email='invitee@test.com',
            role='member',
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertIsNotNone(invitation.token)
        self.assertFalse(invitation.accepted)

    def test_invitation_expiration(self):
        """Test invitation expiration check."""
        # Not expired
        invitation = TeamInvitation.objects.create(
            company=self.company,
            email='invitee@test.com',
            role='member',
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertFalse(invitation.is_expired)

        # Expired
        expired_invitation = TeamInvitation.objects.create(
            company=self.company,
            email='expired@test.com',
            role='member',
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(expired_invitation.is_expired)


class CompanyTeamMethodsTests(TestCase):
    """Tests for Company model team methods."""

    def setUp(self):
        """Set up test data."""
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.admin_user = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.member_user = CustomUser.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            user=self.owner,
            owner=self.owner,
            name='Test Company'
        )

    def test_get_effective_owner(self):
        """Test get_effective_owner returns owner or falls back to user."""
        self.assertEqual(self.company.get_effective_owner(), self.owner)

    def test_get_team_member_count(self):
        """Test team member count."""
        self.assertEqual(self.company.get_team_member_count(), 0)

        TeamMember.objects.create(
            company=self.company,
            user=self.member_user,
            role='member'
        )
        self.assertEqual(self.company.get_team_member_count(), 1)

    def test_can_add_team_member(self):
        """Test seat limit check."""
        # Business tier gets 3 seats
        self.assertTrue(self.company.can_add_team_member())

        # Add 3 members (max for business)
        for i in range(3):
            user = CustomUser.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@test.com',
                password='testpass123'
            )
            TeamMember.objects.create(
                company=self.company,
                user=user,
                role='member'
            )

        # Should not be able to add more
        self.assertFalse(self.company.can_add_team_member())

    def test_is_admin(self):
        """Test admin check."""
        # Owner is always admin
        self.assertTrue(self.company.is_admin(self.owner))

        # Non-member is not admin
        self.assertFalse(self.company.is_admin(self.member_user))

        # Admin role member is admin
        TeamMember.objects.create(
            company=self.company,
            user=self.admin_user,
            role='admin'
        )
        self.assertTrue(self.company.is_admin(self.admin_user))

        # Regular member is not admin
        TeamMember.objects.create(
            company=self.company,
            user=self.member_user,
            role='member'
        )
        self.assertFalse(self.company.is_admin(self.member_user))

    def test_is_member(self):
        """Test membership check."""
        # Owner is a member
        self.assertTrue(self.company.is_member(self.owner))

        # Non-member
        self.assertFalse(self.company.is_member(self.member_user))

        # After joining
        TeamMember.objects.create(
            company=self.company,
            user=self.member_user,
            role='member'
        )
        self.assertTrue(self.company.is_member(self.member_user))


class CustomUserTeamMethodsTests(TestCase):
    """Tests for CustomUser team helper methods."""

    def setUp(self):
        """Set up test data."""
        self.business_user = CustomUser.objects.create_user(
            username='business',
            email='business@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.free_user = CustomUser.objects.create_user(
            username='free',
            email='free@test.com',
            password='testpass123',
            subscription_tier='free'
        )

    def test_get_team_seat_limit(self):
        """Test team seat limit based on tier."""
        self.assertEqual(self.business_user.get_team_seat_limit(), 3)
        self.assertEqual(self.free_user.get_team_seat_limit(), 0)

    def test_has_team_seats(self):
        """Test has_team_seats check."""
        self.assertTrue(self.business_user.has_team_seats())
        self.assertFalse(self.free_user.has_team_seats())

    def test_get_company(self):
        """Test getting user's company."""
        # No company yet
        self.assertIsNone(self.business_user.get_company())

        # After creating company
        company = Company.objects.create(
            user=self.business_user,
            owner=self.business_user,
            name='Test Company'
        )
        self.assertEqual(self.business_user.get_company(), company)

        # Team member can also get company
        TeamMember.objects.create(
            company=company,
            user=self.free_user,
            role='member'
        )
        self.assertEqual(self.free_user.get_company(), company)


class TeamManagementViewTests(TestCase):
    """Tests for team management views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.company = Company.objects.create(
            user=self.owner,
            owner=self.owner,
            name='Test Company'
        )

    def test_team_page_requires_login(self):
        """Test that team page requires authentication."""
        response = self.client.get(reverse('companies:team'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts/login', response.url)

    def test_team_page_requires_team_seats(self):
        """Test that team page requires business tier."""
        free_user = CustomUser.objects.create_user(
            username='free',
            email='free@test.com',
            password='testpass123',
            subscription_tier='free'
        )
        Company.objects.create(
            user=free_user,
            owner=free_user,
            name='Free Company'
        )
        self.client.login(email='free@test.com', password='testpass123')
        response = self.client.get(reverse('companies:team'))
        self.assertEqual(response.status_code, 302)  # Redirects to billing

    def test_team_page_accessible_for_business(self):
        """Test that team page is accessible for business tier."""
        self.client.login(email='owner@test.com', password='testpass123')
        response = self.client.get(reverse('companies:team'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team Settings')

    def test_invite_team_member(self):
        """Test inviting a team member."""
        self.client.login(email='owner@test.com', password='testpass123')
        response = self.client.post(reverse('companies:team_invite'), {
            'email': 'newmember@test.com',
            'role': 'member'
        })
        self.assertEqual(response.status_code, 302)

        # Check invitation was created
        invitation = TeamInvitation.objects.get(email='newmember@test.com')
        self.assertEqual(invitation.company, self.company)
        self.assertEqual(invitation.role, 'member')
        self.assertFalse(invitation.accepted)

    def test_cannot_invite_beyond_seat_limit(self):
        """Test that invitations are blocked when seat limit reached."""
        self.client.login(email='owner@test.com', password='testpass123')

        # Fill up seats with pending invitations
        for i in range(3):
            TeamInvitation.objects.create(
                company=self.company,
                email=f'pending{i}@test.com',
                role='member',
                invited_by=self.owner,
                expires_at=timezone.now() + timedelta(days=7)
            )

        # Try to invite one more
        response = self.client.post(reverse('companies:team_invite'), {
            'email': 'toomany@test.com',
            'role': 'member'
        })
        self.assertEqual(response.status_code, 302)

        # Check invitation was NOT created
        self.assertFalse(
            TeamInvitation.objects.filter(email='toomany@test.com').exists()
        )


class AcceptInvitationViewTests(TestCase):
    """Tests for invitation acceptance."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.company = Company.objects.create(
            user=self.owner,
            owner=self.owner,
            name='Test Company'
        )
        self.invitation = TeamInvitation.objects.create(
            company=self.company,
            email='invitee@test.com',
            role='member',
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7)
        )

    def test_accept_invitation_unauthenticated(self):
        """Test unauthenticated user is redirected to signup."""
        url = reverse('accept_invitation', kwargs={'token': self.invitation.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('signup', response.url)

    def test_accept_invitation_authenticated(self):
        """Test authenticated user can accept invitation."""
        invitee = CustomUser.objects.create_user(
            username='invitee',
            email='invitee@test.com',
            password='testpass123'
        )
        self.client.login(email='invitee@test.com', password='testpass123')

        url = reverse('accept_invitation', kwargs={'token': self.invitation.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Check membership was created
        self.assertTrue(
            TeamMember.objects.filter(
                company=self.company,
                user=invitee
            ).exists()
        )

        # Check invitation was marked as accepted
        self.invitation.refresh_from_db()
        self.assertTrue(self.invitation.accepted)

    def test_cannot_accept_expired_invitation(self):
        """Test expired invitations cannot be accepted."""
        expired_invitation = TeamInvitation.objects.create(
            company=self.company,
            email='expired@test.com',
            role='member',
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(days=1)
        )
        expiry_user = CustomUser.objects.create_user(
            username='expired',
            email='expired@test.com',
            password='testpass123'
        )
        self.client.login(email='expired@test.com', password='testpass123')

        url = reverse('accept_invitation', kwargs={'token': expired_invitation.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Check membership was NOT created
        self.assertFalse(
            TeamMember.objects.filter(
                company=self.company,
                user=expiry_user
            ).exists()
        )


class TeamAwareQuerysetTests(TestCase):
    """Tests for team-aware invoice access."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            subscription_tier='business'
        )
        self.member = CustomUser.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123'
        )
        self.outsider = CustomUser.objects.create_user(
            username='outsider',
            email='outsider@test.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            user=self.owner,
            owner=self.owner,
            name='Test Company'
        )
        TeamMember.objects.create(
            company=self.company,
            user=self.member,
            role='member'
        )

    def test_owner_can_access_invoices(self):
        """Test owner can access invoice list."""
        self.client.login(email='owner@test.com', password='testpass123')
        response = self.client.get(reverse('invoices:list'))
        self.assertEqual(response.status_code, 200)

    def test_member_can_access_invoices(self):
        """Test team member can access invoice list."""
        self.client.login(email='member@test.com', password='testpass123')
        response = self.client.get(reverse('invoices:list'))
        self.assertEqual(response.status_code, 200)

    def test_outsider_sees_empty_list(self):
        """Test non-member sees empty invoice list."""
        # Create a company for the outsider so they can access
        Company.objects.create(
            user=self.outsider,
            owner=self.outsider,
            name='Outsider Company'
        )
        self.client.login(email='outsider@test.com', password='testpass123')
        response = self.client.get(reverse('invoices:list'))
        self.assertEqual(response.status_code, 200)
        # They should see their own empty list, not the team's invoices

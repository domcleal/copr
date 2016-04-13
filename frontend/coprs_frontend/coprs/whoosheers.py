import whoosh

from flask.ext.whooshee import AbstractWhoosheer

from coprs import models
from coprs import whooshee
from coprs import db

@whooshee.register_whoosheer
class CoprUserWhoosheer(AbstractWhoosheer):
    schema = whoosh.fields.Schema(
        copr_id=whoosh.fields.NUMERIC(stored=True, unique=True),
        user_id=whoosh.fields.NUMERIC(stored=True),
        username=whoosh.fields.TEXT(field_boost=2),
        # treat dash as a normal character - so searching for example
        # "copr-dev" will really search for "copr-dev"
        coprname=whoosh.fields.TEXT(
            analyzer=whoosh.analysis.StandardAnalyzer(
                expression=r"\w+(-\.?\w+)*"), field_boost=2),
        chroots=whoosh.fields.TEXT(field_boost=2),
        packages=whoosh.fields.TEXT(
            analyzer=whoosh.analysis.StandardAnalyzer(
                expression=r"\s+", gaps=True), field_boost=2),
        description=whoosh.fields.TEXT(),
        instructions=whoosh.fields.TEXT())

    models = [models.Copr, models.User] # there is StopIteration error when searching if I add models.Package to the list

    @classmethod
    def update_user(cls, writer, user):
        # TODO: this is not needed now, as users can't change names, but may be
        # needed later
        pass

    @classmethod
    def update_copr(cls, writer, copr):
        writer.update_document(copr_id=copr.id,
                               user_id=copr.owner.id,
                               username=copr.owner.name,
                               coprname=copr.name,
                               chroots=cls.get_chroot_names(copr),
                               packages=cls.get_package_names(copr),
                               description=copr.description,
                               instructions=copr.instructions)

    @classmethod
    def update_package(cls, writer, package):
        writer.update_document(copr_id=package.copr.id, packages=cls.get_package_names(package.copr))

    @classmethod
    def insert_user(cls, writer, user):
        # nothing, user doesn't have coprs yet
        pass

    @classmethod
    def insert_copr(cls, writer, copr):
        writer.add_document(copr_id=copr.id,
                            user_id=copr.owner.id,
                            username=copr.owner.name,
                            coprname=copr.name,
                            chroots=cls.get_chroot_names(copr),
                            packages=cls.get_package_names(copr),
                            description=copr.description,
                            instructions=copr.instructions)

    @classmethod
    def insert_package(cls, writer, package):
        writer.update_document(copr_id=package.copr.id, packages=cls.get_package_names(package.copr))

    @classmethod
    def delete_copr(cls, writer, copr):
        writer.delete_by_term("copr_id", copr.id)

    @classmethod
    def delete_package(cls, writer, package):
        writer.update_document(copr_id=package.copr.id, packages=cls.get_package_names(package.copr))

    @classmethod
    def get_chroot_names(cls, copr):
        # NOTE: orm db session for Copr model is already commited at the point insert_*/update_* methods are called.
        # Hence we use db.engine directly (for a new session).
        result = db.engine.execute(
            """
            SELECT os_release, os_version, arch
            FROM mock_chroot
            JOIN copr_chroot ON copr_chroot.mock_chroot_id=mock_chroot.id
            WHERE copr_chroot.copr_id={0}
            """.format(copr.id)
        )
        return ["{}-{}-{}".format(row[0], row[1], row[2]) for row in result.fetchall()]

    @classmethod
    def get_package_names(cls, copr):
        result = db.engine.execute(
            """
            SELECT name
            FROM package
            WHERE copr_id={0}
            """.format(copr.id)
        )
        return [row[0] for row in result.fetchall()]

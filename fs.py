import zlib
import sys
import llfuse
import errno
import stat
import logging
from llfuse import FUSEError
import pywikibot
from bidict import bidict

log = logging.getLogger()

class Operations(llfuse.Operations):
    def __init__(self):
        super(Operations, self).__init__()
        self.map = bidict()
        self.site = pywikibot.Site()
        ## Insert root directory
        #self.cursor.execute("INSERT INTO inodes (id,mode,uid,gid,mtime,atime,ctime) "
        #                    "VALUES (?,?,?,?,?,?,?)",
        #                    (llfuse.ROOT_INODE, stat.S_IFDIR | stat.S_IRUSR | stat.S_IWUSR
        #                      | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH
        #                      | stat.S_IXOTH, os.getuid(), os.getgid(), time(),
        #                      time(), time()))
        #self.cursor.execute("INSERT INTO contents (name, parent_inode, inode) VALUES (?,?,?)",
        #                    (b'..', llfuse.ROOT_INODE, llfuse.ROOT_INODE))
        self.nonexistent = 0
        self.existent = 0
        self.exists = []

    def lookup(self, inode_p, name):
        page = pywikibot.Page(self.site, title=name.decode("utf-8"))
        if not page.exists():
            log.debug("{} does not exist, parent {}".format(name, inode_p))
            self.nonexistent += 1
            raise(llfuse.FUSEError(errno.ENOENT))

        self.exists += [page.title()]

        return self.getattr(self.titleToInode(page.title()))

    def titleToInode(self, title):
        self.map[title] = zlib.adler32(title.encode("utf-8"))
        return self.map[title]

    def getattr(self, inode):
        entry = llfuse.EntryAttributes()
        entry.st_ino = inode
        entry.generation = 0
        entry.entry_timeout = 300
        entry.attr_timeout = 300
        entry.st_mode = (stat.S_IRUSR | stat.S_IWUSR
                              | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH
                              | stat.S_IXOTH)
        entry.st_nlink = 1
        entry.st_uid = 1000
        entry.st_gid = 1000
        entry.st_rdev = 0
        try:
            pg = pywikibot.Page(self.site, title=self.map.inv[inode])
            self.existent += 1
            entry.st_size = len(pg.text.encode("utf-8"))
            entry.st_mtime = pg.editTime().timestamp()
            entry.st_ctime = pg.oldest_revision.timestamp.timestamp()
        except KeyError:
            log.debug("tried getting inode {}, it does not exist".format(inode))
            self.nonexistent += 1
            entry.st_size = 0
            entry.st_mtime = 0
            entry.st_ctime = 0
        if inode == llfuse.ROOT_INODE:
            log.debug("getattr root")
            entry.st_mode |= stat.S_IFDIR
            self.st_nlink = 1 + self.nonexistent + self.existent
        else:
            entry.st_mode |= stat.S_IFREG
        entry.st_blksize = 512
        entry.st_blocks = 1
        entry.st_atime = 0

        return entry

    def readlink(self, inode):
        raise llfuse.FUSEError(errno.ENOSYS)

    def opendir(self, inode):
        log.debug("opendir")
        return llfuse.ROOT_INODE

    def readdir(self, inode, off):
        log.debug("readdir")
        return []

    def unlink(self, inode_p, name):
        #if stat.S_ISDIR(entry.st_mode):
        #    raise llfuse.FUSEError(errno.EISDIR)
        raise llfuse.FUSEError(errno.ENOSYS)

    def rmdir(self, inode_p, name):
        #if not stat.S_ISDIR(entry.st_mode):
        #    raise llfuse.FUSEError(errno.ENOTDIR)
        raise llfuse.FUSEError(errno.ENOSYS)

    def symlink(self, inode_p, name, target, ctx):
        raise llfuse.FUSEError(errno.ENOSYS)

    def rename(self, inode_p_old, name_old, inode_p_new, name_new):
        raise llfuse.FUSEError(errno.ENOSYS)

    def link(self, inode, new_inode_p, new_name):
        raise llfuse.FUSEError(errno.ENOSYS)

    def setattr(self, inode, attr):
        raise llfuse.FUSEError(errno.ENOSYS)

    def mknod(self, inode_p, name, mode, rdev, ctx):
        raise llfuse.FUSEError(errno.ENOSYS)

    def mkdir(self, inode_p, name, mode, ctx):
        raise llfuse.FUSEError(errno.ENOSYS)

    def statfs(self):
        stat_ = llfuse.StatvfsData()

        stat_.f_bsize = 512
        stat_.f_frsize = 512

        size = 9000
        stat_.f_blocks = size // stat_.f_frsize
        stat_.f_bfree = max(size // stat_.f_frsize, 1024)
        stat_.f_bavail = stat_.f_bfree

        inodes = 9000
        stat_.f_files = inodes
        stat_.f_ffree = max(inodes , 100)
        stat_.f_favail = stat_.f_ffree

        return stat_

    def open(self, inode, flags):
        log.debug("open")
        return inode

    def access(self, inode, mode, ctx):
        return True

    def create(self, inode_parent, name, mode, flags, ctx):
        raise llfuse.FUSEError(errno.ENOSYS)

    def read(self, fh, offset, length):
        log.debug("read")
        return pywikibot.Page(self.site, self.map.inv[fh]).text.encode("utf-8")[offset:offset+length]

    def write(self, fh, offset, buf):
        raise llfuse.FUSEError(errno.ENOSYS)

    def release(self, fh):
        log.debug("release {}".format(fh))

def init_logging():
    formatter = logging.Formatter('%(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)

if __name__ == '__main__':

    if len(sys.argv) != 2:
        raise SystemExit('Usage: %s <mountpoint>' % sys.argv[0])

    init_logging()
    mountpoint = sys.argv[1]
    operations = Operations()

    llfuse.init(operations, mountpoint,
                [  'fsname=tmpfs', "nonempty" ])

    try:
        llfuse.main(single=True)
    except:
        llfuse.close(unmount=False)
        raise

    llfuse.close()

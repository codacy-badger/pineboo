import os
import sys
from PyQt5.QtCore import QTime
from pineboolib.fllegacy.FLSqlQuery import FLSqlQuery
from pineboolib.fllegacy.FLSqlCursor import FLSqlCursor
from pineboolib.utils import auto_qt_translate_text
from pineboolib.fllegacy.FLUtil import FLUtil
import traceback
from PyQt5.Qt import QDomDocument, qApp, QDateTime, QProgressDialog, QDate, QRegExp


class QApplication:
    @staticmethod
    def tr(text, *args):
        return text


class FLSQLITE(object):

    version_ = None
    conn_ = None
    name_ = None
    alias_ = None
    errorList = None
    lastError_ = None
    declare = None
    db_filename = None
    sql = None
    rowsFetched = None
    db_ = None
    mobile_ = True
    # True por defecto, convierte los datos de entrada y salida a UTF-8 desde
    # Latin1
    parseFromLatin = None

    def __init__(self):
        self.version_ = "0.5"
        self.conn_ = None
        self.name_ = "FLsqlite"
        self.open_ = False
        self.errorList = []
        self.alias_ = "SQLite3"
        self.declare = []
        self.db_filename = None
        self.sql = None
        self.rowsFetched = {}
        self.db_ = None
        self.parseFromLatin = False
        self.mobile_ = True

    def version(self):
        return self.version_

    def driverName(self):
        return self.name_

    def isOpen(self):
        return self.open_

    def connect(self, db_name, db_host, db_port, db_userName, db_password):

        self.db_filename = db_name
        db_is_new = not os.path.exists(self.db_filename)

        try:
            import sqlite3
        except ImportError:
            print(traceback.format_exc())
            print("HINT: Instale el paquete python3-sqlite3 e intente de nuevo")
            sys.exit(0)

        self.conn_ = sqlite3.connect(self.db_filename)
        self.conn_.isolation_level = None

        if db_is_new:
            print("La base de datos %s no existe" % self.db_filename)

        if self.conn_:
            self.open_ = True

        if self.parseFromLatin:
            self.conn_.text_factory = lambda x: str(x, 'latin1')

        return self.conn_

    def formatValue(self, type_, v, upper):

        util = FLUtil()

        s = None
        # TODO: psycopg2.mogrify ???
        if type_ == "pixmap" and v.find("'") > -1:
            v = self.normalizeValue(v)

        if type_ == "bool" or type_ == "unlock":
            if isinstance(v, str):
                if v[0].lower() == "t":
                    s = 1
                else:
                    s = 0
            elif isinstance(v, bool):
                if v:
                    s = 1
                else:
                    s = 0

        elif type_ == "date":
            s = "'%s'" % util.dateDMAtoAMD(v)

        elif type_ == "time":
            if v:
                s = "'%s'" % v
            else:
                s = ""

        elif type_ in ("uint", "int", "double", "serial"):
            if v:
                s = 0
            else:
                s = v

        else:
            v = auto_qt_translate_text(v)
            if upper and type_ == "string":
                v = v.upper()
                # v = v.encode("UTF-8")
            s = "'%s'" % v
        # print ("PNSqlDriver(%s).formatValue(%s, %s) = %s" % (self.name_, type_, v, s))
        return s

    def DBName(self):
        return self.db_filename[self.db_filename.rfind("/") + 1:-5]

    def canOverPartition(self):
        return True

    def nextSerialVal(self, table, field):
        q = FLSqlQuery()
        q.setSelect("max(%s)" % field)
        q.setFrom(table)
        q.setWhere("1 = 1")
        if not q.exec_():  # FIXME: exec es palabra reservada
            print("not exec sequence")
            return None
        if q.first():
            return int(q.value(0)) + 1
        else:
            return None

    def savePoint(self, n):
        if not self.isOpen():
            print("SQL3Driver::savePoint: Database not open")
            return False

        cursor = self.conn_.cursor()
        try:
            cursor.execute("SAVEPOINT sv_%s" % n)
        except Exception:
            self.setLastError(
                "No se pudo crear punto de salvaguarda", "SAVEPOINT sv_%s" % n)
            print("SQL3Driver:: No se pudo crear punto de salvaguarda SAVEPOINT sv_%s" %
                  n, traceback.format_exc())
            return False

        return True

    def canSavePoint(self):
        return True

    def rollbackSavePoint(self, n):
        if not self.isOpen():
            print("SQL3Driver::rollbackSavePoint: Database not open")
            return False

        cursor = self.conn_.cursor()
        try:
            cursor.execute("ROLLBACK TRANSACTION TO SAVEPOINT sv_%s" % n)
        except Exception:
            self.setLastError(
                "No se pudo rollback a punto de salvaguarda", "ROLLBACK TO SAVEPOINTt sv_%s" % n)
            print("SQL3Driver:: No se pudo rollback a punto de salvaguarda ROLLBACK TO SAVEPOINT sv_%s" %
                  n, traceback.format_exc())
            return False

        return True

    def setLastError(self, text, command):
        self.lastError_ = "%s (%s)" % (text, command)

    def lastError(self):
        return self.lastError_

    def commitTransaction(self):
        if not self.isOpen():
            print("SQL3Driver::commitTransaction: Database not open")

        cursor = self.conn_.cursor()
        try:
            cursor.execute("COMMIT TRANSACTION")
        except Exception:
            self.setLastError("No se pudo aceptar la transacción", "COMMIT")
            print("SQL3Driver:: No se pudo aceptar la transacción COMMIT",
                  traceback.format_exc())
            return False

        return True

    def rollbackTransaction(self):
        if not self.isOpen():
            print("SQL3Driver::rollbackTransaction: Database not open")

        cursor = self.conn_.cursor()
        try:
            cursor.execute("ROLLBACK TRANSACTION")
        except Exception:
            self.setLastError("No se pudo deshacer la transacción", "ROLLBACK")
            print("SQL3Driver:: No se pudo deshacer la transacción ROLLBACK",
                  traceback.format_exc())
            return False

        return True

    def transaction(self):
        if not self.isOpen():
            print("SQL3Driver::transaction: Database not open")

        cursor = self.conn_.cursor()
        try:
            cursor.execute("BEGIN TRANSACTION")
        except Exception:
            self.setLastError("No se pudo crear la transacción", "BEGIN")
            print("SQL3Driver:: No se pudo crear la transacción BEGIN",
                  traceback.format_exc())
            return False

        return True

    def releaseSavePoint(self, n):

        if not self.isOpen():
            print("SQL3Driver::releaseSavePoint: Database not open")
            return False

        cursor = self.conn_.cursor()
        try:
            cursor.execute("RELEASE SAVEPOINT sv_%s" % n)
        except Exception:
            self.setLastError(
                "No se pudo release a punto de salvaguarda", "RELEASE SAVEPOINT sv_%s" % n)
            print("SQL3Driver:: No se pudo release a punto de salvaguarda RELEASE SAVEPOINT sv_%s" %
                  n, traceback.format_exc())

            return False

        return True

    def setType(self, type_, leng=None):
        if leng:
            return " %s(%s)" % (type_.upper(), leng)
        else:
            return " %s" % type_.upper()

    def refreshQuery(self, curname, fields, table, where, cursor, conn):
        self.sql = "SELECT %s FROM %s WHERE %s" % (fields, table, where)

    def refreshFetch(self, number, curname, table, cursor, fields, where):
        try:
            cursor.execute(self.sql)
            rows = cursor.fetchmany(number)
            return rows
        except Exception:
            print("SQL3Driver:: refreshFetch", traceback.format_exc())

    def useThreads(self):
        return False

    def useTimer(self):
        return True

    def fetchAll(self, cursor, tablename, where_filter, fields, curname):
        if curname not in self.rowsFetched.keys():
            self.rowsFetched[curname] = 0
        try:
            cursor.execute(self.sql)
            rows = cursor.fetchall()
            rowsF = []
            if self.rowsFetched[curname] < len(rows):
                i = 0
                for row in rows:
                    i = i + 1
                    if i > self.rowsFetched[curname]:
                        rowsF.append(row)

                self.rowsFetched[curname] = i
            return rowsF
        except Exception:
            print("SQL3Driver:: fetchAll", traceback.format_exc())
            return []

    def existsTable(self, name):
        if not self.isOpen():
            return False

        t = FLSqlQuery()
        t.setForwardOnly(True)
        ok = t.exec_("SELECT * FROM %s WHERE 1 = 1 LIMIT 1" % name)
        if ok:
            ok = t.next()

        del t
        return ok

    def sqlCreateTable(self, tmd):
        if not tmd:
            return None

        primaryKey = None
        sql = "CREATE TABLE %s (" % tmd.name()

        fieldList = tmd.fieldList()

        unlocks = 0
        for field in fieldList:
            if field.type() == "unlock":
                unlocks = unlocks + 1

        if unlocks > 1:
            print(u"FLManager : No se ha podido crear la tabla " + tmd.name())
            print(
                u"FLManager : Hay mas de un campo tipo unlock. Solo puede haber uno.")
            return None

        i = 1
        for field in fieldList:
            sql = sql + field.name()
            if field.type() == "int":
                sql = sql + " INTEGER"
            elif field.type() == "uint":
                sql = sql + " INTEGER"
            elif field.type() in ("bool", "unlock"):
                sql = sql + " BOOLEAN"
            elif field.type() == "double":
                sql = sql + " FLOAT"
            elif field.type() == "time":
                sql = sql + " VARCHAR(20)"
            elif field.type() == "date":
                sql = sql + " VARCHAR(20)"
            elif field.type() == "pixmap":
                sql = sql + " TEXT"
            elif field.type() == "string":
                sql = sql + " VARCHAR"
            elif field.type() == "stringlist":
                sql = sql + " TEXT"
            elif field.type() == "bytearray":
                sql = sql + " CLOB"
            elif field.type() == "serial":
                sql = sql + " INTEGER"
                if not field.isPrimaryKey():
                    sql = sql + " PRIMARY KEY"

            longitud = field.length()
            if longitud > 0:
                sql = sql + "(%s)" % longitud

            if field.isPrimaryKey():
                if primaryKey is None:
                    sql = sql + " PRIMARY KEY"
                else:
                    print(QApplication.tr("FLManager : Tabla-> ") + tmd.name() +
                          QApplication.tr(" . Se ha intentado poner una segunda clave primaria para el campo ") +
                          field.name() + QApplication.tr(" , pero el campo ") + primaryKey +
                          QApplication.tr(" ya es clave primaria. Sólo puede existir una clave primaria en FLTableMetaData, "
                                          "use FLCompoundKey para crear claves compuestas."))
                    return None
            else:
                if field.isUnique():
                    sql = sql + " UNIQUE"
                if not field.allowNull():
                    sql = sql + " NOT NULL"
                else:
                    sql = sql + " NULL"

            if not i == len(fieldList):
                sql = sql + ","
                i = i + 1

        sql = sql + ");"

        createIndex = "CREATE INDEX %s_pkey ON %s (%s)" % (
            tmd.name(), tmd.name(), tmd.primaryKey())

        #q = FLSqlQuery()
        # q.setForwardOnly(True)
        # q.exec_(createIndex)
        sql += createIndex

        return sql

    def mismatchedTable(self, table1, tmd_or_table2, db_):
        if isinstance(tmd_or_table2, str):
            mtd = db_.manager().metadata(tmd_or_table2, True)
            if not mtd:
                return False

            recMtd = self.recordInfo(tmd_or_table2)
            recBd = self.recordInfo2(table1)
            # fieldBd = None
            mismatch = False
            try:
                for fieldMtd in recMtd:
                    # fieldBd = None
                    found = False
                    for field in recBd:
                        if field[0] == fieldMtd[0]:
                            found = True
                            if self.notEqualsFields(field, fieldMtd):
                                mismatch = True
                            break

                    if not found:
                        mismatch = True
                        break

            except Exception:
                print(traceback.format_exc())

            return mismatch

        else:
            return self.mismatchedTable(table1, tmd_or_table2.name(), db_)

    def notEqualsFields(self, field1, field2):
        ret = False
        try:
            if not field1[2] == field2[2] and not field2[6]:
                ret = True

            if field1[1] == "stringlist" and not field2[1] in ("stringlist", "pixmap"):
                ret = True

            elif field1[1] == "string" and (not field2[1] in ("string", "time", "date") or not field1[3] == field2[3]):
                if field2[1] in ("time", "date") and field1[3] == 20:
                    ret = False
                else:
                    ret = True

            elif field1[1] == "uint" and not field2[1] in ("int", "uint", "serial"):
                ret = True
            elif field1[1] == "bool" and not field2[1] in ("bool", "unlock"):
                ret = True
            elif field1[1] == "double" and not field2[1] == "double":
                ret = True

            if ret:
                print(field1, field2)
        except Exception:
            print(traceback.format_exc())
        return ret

    def recordInfo2(self, tablename):
        if not self.isOpen():
            return None

        sql = "PRAGMA table_info('%s')" % tablename
        conn = self.conn_
        cursor = conn.execute(sql)
        res = cursor.fetchall()
        return self.recordInfo(res)

    def recordInfo(self, tablename_or_query):
        if not self.isOpen():
            return None

        info = []

        if isinstance(tablename_or_query, str):
            tablename = tablename_or_query

            doc = QDomDocument(tablename)
            stream = self.db_.managerModules().contentCached("%s.mtd" % tablename)
            util = FLUtil()
            if not util.domDocumentSetContent(doc, stream):
                print(
                    "FLManager : " + qApp.tr("Error al cargar los metadatos para la tabla %1").arg(tablename))

                return self.recordInfo2(tablename)

            docElem = doc.documentElement()
            mtd = self.db_.manager().metadata(docElem, True)
            if not mtd:
                return self.recordInfo2(tablename)
            fL = mtd.fieldList()
            if not fL:
                del mtd
                return self.recordInfo2(tablename)

            for f in mtd.fieldsNames():
                field = mtd.field(f)
                info.append([field.name(), field.type(), not field.allowNull(), field.length(
                ), field.partDecimal(), field.defaultValue(), field.isPrimaryKey()])

            del mtd
            return info

        else:
            for columns in tablename_or_query:
                fName = columns[1]
                fType = columns[2]
                fSize = 0
                fAllowNull = (columns[3] == 0)
                if fType.find("VARCHAR(") > -1:
                    fSize = int(fType[fType.find("(") + 1: len(fType) - 1])

                info.append([fName, self.decodeSqlType(
                    fType), not fAllowNull, fSize])

            return info

    def decodeSqlType(self, type):
        ret = None
        if type == "BOOLEAN":  # y unlock
            ret = "bool"
        elif type == "FLOAT":
            ret = "double"
        elif type.find("VARCHAR") > -1:  # Aqui también puede ser time y date
            ret = "string"
        elif type == "TEXT":  # Aquí también puede ser pixmap
            ret = "stringlist"
        elif type == "INTEGER":  # serial
            ret = "uint"

        return ret

    def alterTable(self, mtd1, mtd2, key):
        util = FLUtil()

        oldMTD = None
        newMTD = None
        doc = QDomDocument("doc")
        docElem = None

        if not util.docDocumentSetContect(doc, mtd1):
            print("FLManager::alterTable : " +
                  qApp.tr("Error al cargar los metadatos."))
        else:
            docElem = doc.documentElement()
            oldMTD = self.db_.manager().metadata(docElem, True)

        if oldMTD and oldMTD.isQuery():
            return True

        if not util.docDocumentSetContect(doc, mtd2):
            print("FLManager::alterTable : " +
                  qApp.tr("Error al cargar los metadatos."))
            return False
        else:
            docElem = doc.documentElement()
            newMTD = self.db_.manager().metadata(docElem, True)

        if not oldMTD:
            oldMTD = newMTD

        if not oldMTD.name() == newMTD.name():
            print("FLManager::alterTable : " +
                  qApp.tr("Los nombres de las tablas nueva y vieja difieren."))
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        oldPK = oldMTD.primaryKey()
        newPK = newMTD.primaryKey()

        if not oldPK == newPK:
            print("FLManager::alterTable : " +
                  qApp.tr("Los nombres de las claves primarias difieren."))
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        if not self.db_.manager().checkMetaData(oldMTD, newMTD):
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return True

        if not self.db_.manager().existsTable(oldMTD.name()):
            print("FLManager::alterTable : " + qApp.tr(
                "La tabla %1 antigua de donde importar los registros no existe.").arg(oldMTD.name()))
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        fieldList = oldMTD.fieldList()
        oldField = None

        if not fieldList:
            print("FLManager::alterTable : " +
                  qApp.tr("Los antiguos metadatos no tienen campos."))
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        renameOld = "%salteredtable%s" % (
            oldMTD.name()[0:5], QDateTime().currentDateTime().toString("ddhhssz"))

        if not self.db_.dbAux():
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        self.db_.dbAux().transaction()

        if key and len(key) == 40:
            c = FLSqlCursor("flfiles", True, self.db_.dbAux())
            c.setForwardOnly(True)
            c.setFilter("nombre = '%s.mtd'" % renameOld)
            c.select()
            if not c.next():
                buffer = c.primeInsert()
                buffer.setValue("nombre", "%s.mtd" % renameOld)
                buffer.setValue("contenido", mtd1)
                buffer.setValue("sha", key)
                c.insert()

        q = FLSqlQuery("", self.db_.dbAux())
        if not q.exec_("CREATE TABLE %s AS SELECT * FROM %s;" % (renameOld, oldMTD.name())) or not q.exec_("DROP TABLE %s;" % oldMTD.name()):
            print("FLManager::alterTable : " +
                  qApp.tr("No se ha podido renombrar la tabla antigua."))

            self.db_.dbAux().rollback()
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        if not self.db_.manager().createTable(newMTD):
            self.db_.dbAux().rollback()
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        oldCursor = FLSqlCursor(renameOld, True, self.db_.dbAux())
        oldCursor.setModeAccess(oldCursor.Browse)
        newCursor = FLSqlCursor(newMTD.name(), True, self.db_.dbAux())
        newCursor.setMode(newCursor.Insert)

        oldCursor.select()
        totalSteps = oldCursor.size()
        progress = QProgressDialog(qApp.tr("Reestructurando registros para %1...").arg(
            newMTD.alias()), qApp.tr("Cancelar"), 0, totalSteps)
        progress.setLabelText(qApp.tr("Tabla modificada"))

        step = 0
        newBuffer = None
        # sequence = ""
        fieldList = newMTD.fieldList()
        newField = None

        if not fieldList:
            print("FLManager::alterTable : " +
                  qApp.tr("Los nuevos metadatos no tienen campos."))
            self.db_.dbAux().rollback()
            if oldMTD and not oldMTD == newMTD:
                del oldMTD
            if newMTD:
                del newMTD

            return False

        v = None
        ok = True
        while oldCursor.next():
            v = None
            newBuffer = newCursor.primeInsert()

            for it in fieldList:
                oldField = oldMTD.field(newField.name())
                if not oldField or not oldCursor.field(oldField.name()):
                    if not oldField:
                        oldField = newField

                    v = newField.defaultValue()

                else:
                    v = oldCursor.value(newField.name())
                    if (not oldField.allowNull() or not newField.allowNull()) and (v is None):
                        defVal = newField.defaultValue()
                        if defVal is not None:
                            v = defVal

                    if not newBuffer.field(newField.name()).type() == newField.type():
                        print("FLManager::alterTable : " + qApp.tr("Los tipos del campo %1 no son compatibles. Se introducirá un valor nulo.")
                              .arg(newField.name()))

                if not oldField.allowNull() or not newField.allowNull() and v is not None:
                    if oldField.type() in ("int", "serial", "uint", "bool", "unlock"):
                        v = 0
                    elif oldField.type() == "double":
                        v = 0.0
                    elif oldField.type() == "time":
                        v = QTime().currentTime()
                    elif oldField.type() == "date":
                        v = QDate().currentDate()
                    else:
                        v = "NULL"[0:newField.length()]

                newBuffer.setValue(newField.name(), v)

            if not newCursor.insert():
                ok = False
                break
            step = step + 1
            progress.setProgress(step)

        progress.setProgress(totalSteps)
        if oldMTD and not oldMTD == newMTD:
            del oldMTD
        if newMTD:
            del newMTD

        if ok:
            self.db_.dbAux().commit()
        else:
            self.db_.dbAux().rollback()
            return False

        return True

    def tables(self, typeName=None):
        tl = []
        if not self.isOpen():
            return tl

        t = FLSqlQuery()
        t.setForwardOnly(True)

        if typeName == "Tables" and typeName == "Views":
            t.exec_(
                "SELECT name FROM sqlite_master WHERE type='table' OR type='view'")
        elif not typeName or typeName == "Tables":
            t.exec_("SELECT name FROM sqlite_master WHERE type='table'")
        elif not typeName or typeName == "Views":
            t.exec_("SELECT name FROM sqlite_master WHERE type='view'")

        while t.next():
            tl.append(str(t.value(0)))

        if not typeName or typeName == "SystemTables":
            tl.append("sqlite_master")

        del t
        return tl

    def normalizeValue(self, text):
        if text is None:
            return ""

        ret = ""
        for c in text:
            if c == "'":
                c = "''"

            ret = ret + c

        if self.parseFromLatin:
            ret = ret  # Estoy hay que arreglarlo si alguien quiere trabajar con latin1

        return ret

    def queryUpdate(self, name, update, filter):
        sql = "UPDATE %s SET %s WHERE %s" % (name, update, filter)
        return sql

    def Mr_Proper(self):
        util = FLUtil()
        self.db_.dbAux().transaction()
        rx = QRegExp("^.*[\\d][\\d][\\d][\\d].[\\d][\\d].*[\\d][\\d]$")
        rx2 = QRegExp("^.*alteredtable[\\d][\\d][\\d][\\d].*$")
        qry = FLSqlQuery(None, self.db_.dbAux())
        qry2 = FLSqlQuery(None, self.db_.dbAux())
        steps = 0
        item = ""

        rx3 = QRegExp("^.*\\d{6,9}$")
        listOldBks = rx3 in self.tables("")

        qry.exec_("select nombre from flfiles")
        util.createProgressDialog(
            util.tr("Borrando backups"), len(listOldBks) + qry.size() + 5)
        while qry.next():
            item = qry.value(0)
            if item.find(rx) > -1 or item.find(rx2) > -1:
                util.setLabelText(util.tr("Borrando regisro %1").arg(item))
                qry2.exec_("delete from flfiles where nombre = '%s'" % item)
                if item.find("alteredtable") > -1:
                    if item.replace(".mtd", "") in self.tables(""):
                        util.setLabelText(
                            util.tr("Borrando tabla %1").arg(item))
                        qry2.exec_("drop table %s" %
                                   (item.replace(".mtd", "")))

            steps = steps + 1
            util.setProgress(steps)

        for item in listOldBks:
            if item in self.tables(""):
                util.setLabelText(util.tr("Borrando tabla %1").arg(item))
                qry2.exec_("drop table %s" % item)

            steps = steps + 1
            util.setProgress(steps)

        util.setLabelText(util.tr("Inicializando cachés"))
        steps = steps + 1
        util.setProgress(steps)

        qry.exec_("delete from flmetadata")
        qry.exec_("delete from flvar")
        self.db_.manager().cleanupMetaData()
        self.db_.dbAux().commit()

        util.setLabelText(util.tr("Vacunando base de datos"))
        steps = steps + 1
        util.setProgress(steps)
        qry2.exec_("vacuum")
        steps = steps + 1
        util.setProgress(steps)
        util.destryProgressDialog()

    def cascadeSupport(self):
        return False

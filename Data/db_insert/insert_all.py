import insert_1st as first
import insert2db2 as qpoll
import insert_2nd as second

if __name__ == "__main__":
    print("\n----------------------------------------\n")
    print(">>>ETL 작업 시작.\n")
    print("\n----------------------------------------\n")
    first.main()
    print("\n----------------------------------------\n")
    print(">>> Welcome 1st ETL 작업 완료.\n")
    print("----------------------------------------\n")
    qpoll.main()
    print("\n----------------------------------------\n")
    print(">>> qpoll_... ETL 작업 완료.\n")
    print("----------------------------------------\n")
    second.main()
    print("\n----------------------------------------\n")
    print(">>> Welcome 2nd ETL 작업 완료.\n")
    print("----------------------------------------\n")
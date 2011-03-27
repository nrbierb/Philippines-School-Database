def merge_lists(mergelist, addlist):
    if (len(mergelist) == 0):
        newlist = addlist
    else:
        newlist = []
        for member in mergelist:
            if (member[0]< addlist[0][0]):
                #The most common case.
                newlist.append(member)
                continue
            if (member[0] == addlist[0][0]):
                #There is an object in both lists that have the
                #same name. Add the higher priorty addlist one to
                # the results list
                priority_member = addlist.pop(0)
                newlist.append(priority_member)
                continue
            if (member[0] > addlist[0][0]):
                #The object in the add list needs to be added just
                #after the object from the mergelist
                add_member = addlist.pop(0)
                newlist.append(member)
                newlist.append(add_member)
        #now add antyhing left in the add list to the end
        if (len(addlist) > 0):
            newlist.extend(addlist)                
    return newlist

def merge_lists1(mergelist, addlist):
    if (len(mergelist) == 0):
        #the initial condition
        newlist = addlist
    elif (len(addlist) == 0):
        #a common cae whre the addlist is empty
        newlist = mergelist 
    else:
        newlist = []
        while ((len(mergelist) > 0) and (len(addlist) > 0)):
            if (mergelist[0][0]< addlist[0][0]):
                #The most common case where there is a member
                #of the merge list ready to add
                merge_obj = mergelist.pop(0)
                newlist.append(merge_obj)
                continue
            if (mergelist[0][0] == addlist[0][0]):
                #There is an object in both lists that have the
                #same name. Add the higher priorty addlist one to
                # the results list
                merge_obj = mergelist.pop(0)
                add_obj = addlist.pop(0)
                newlist.append(add_obj)
                continue
            if (mergelist[0][0] > addlist[0][0]):
                #The object in the add list needs to be added 
                add_obj = addlist.pop(0)
                newlist.append(add_obj)
        #now add antyhing left in either of the lists to the end
        if (len(mergelist) > 0):
            newlist.extend(mergelist)
        elif (len(addlist) > 0):
            newlist.extend(addlist)              
    return newlist

a = [(0,1),(1,1),(3,3),(5,5),(7,7)]
b = [(0,0),(4,4),(5,6),(6,6),(7,8)]

c = merge_lists1([],b)
print c
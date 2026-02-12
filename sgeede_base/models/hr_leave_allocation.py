from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta
from math import floor, ceil
from odoo.exceptions import ValidationError

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    allocation_id = fields.Many2one('hr.leave.allocation', string='Allocation')
    allocation_ids = fields.One2many('hr.leave.allocation', 'allocation_id', string='Allocation Details')

    def _prorate(self, months, value):
        prorated = (months * value) / 12
        # Use a small epsilon to handle floating point precision issues (e.g. 3.499999999 -> 3.5)
        return ceil(prorated) if (prorated % 1) >= 0.499999 else floor(prorated)

    def _meets_minimum(self, diff, min_service, min_type):
        if min_type == 'day' and diff.days < min_service:
            return False
        if min_type == 'month' and (diff.years * 12 + diff.months) < min_service:
            return False
        if min_type == 'year' and diff.years < min_service:
            return False
        return True

    def calculate_annual_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'annual':
                continue

            employee = alloc.employee_id
            leave_type = alloc.holiday_status_id

            if not employee or not employee.join_date or not alloc.date_from:
                alloc.number_of_days = 0
                continue

            join = fields.Date.from_string(employee.join_date)
            base = fields.Date.from_string(alloc.date_from)

            diff = relativedelta(base, join)
            total_months = diff.years * 12 + diff.months + (1 if diff.days > 0 else 0)

            if not self._meets_minimum(diff, leave_type.allocation_min, leave_type.min_type):
                raise ValidationError(_("Employee has not met minimum service requirement"))

            configs = leave_type.leave_config_ids.sorted(key=lambda x: x.years_count)
            if not configs:
                alloc.number_of_days = 0
                continue

            years = diff.years
            
            # Find the correct configuration for the employee's years of service completed
            years_to_check = years
            cfg = configs[0]
            for c in configs:
                if years_to_check >= c.years_count:
                    cfg = c
                else:
                    break
            
            added = cfg.added_value

            alloc.allocation_ids.unlink()

            if years < configs[0].years_count:
                prorated = self._prorate(total_months, added)
                alloc.number_of_days = prorated
                self._generate_future_allocations(alloc, join, base, added, configs[0].years_count, prorated)
                continue

            alloc.number_of_days = added

        return True

    def _generate_future_allocations(self, alloc, join, base, added_value, smallest_year, previous_total):
        # Calculate anniversary date and end of the anniversary month
        one_year_date = join + relativedelta(years=smallest_year)
        one_year_end_date = one_year_date + relativedelta(day=31)
        current = base + relativedelta(months=1)

        # Use first of month comparison to ensure we capture the anniversary month regardless of the day
        while current.replace(day=1) <= one_year_date.replace(day=1):
            diff = relativedelta(current, join)
            total_months = diff.years * 12 + diff.months

            # Cap months at 12 for the anniversary month calculation
            if current.replace(day=1) == one_year_date.replace(day=1):
                total_months = smallest_year * 12

            new_total = self._prorate(total_months, added_value)
            increment = new_total - previous_total

            if increment > 0:
                # Use the cycle date as date_from (e.g. 6 Nov) and the end of the month as date_to
                # to ensure Start Date <= End Date even if anniversary is earlier in the month
                self.env['hr.leave.allocation'].with_context(skip_leave_calculation=True).create({
                    'allocation_id': alloc.id,
                    'employee_id': alloc.employee_id.id,
                    'holiday_status_id': alloc.holiday_status_id.id,
                    'date_from': current,
                    'date_to': one_year_end_date,
                    'number_of_days': increment,
                })
                alloc.date_to = one_year_end_date
                previous_total = new_total

            current += relativedelta(months=1)

    
    def calculate_sick_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type not in ['sick', 'hospitalisation']:
                continue

            employee = alloc.employee_id
            leave_type = alloc.holiday_status_id
            join_date = employee.join_date
            base_date = alloc.date_from

            if not employee or not join_date or not base_date:
                alloc.number_of_days = 0
                continue

            join_date = fields.Date.from_string(join_date)
            base_date = fields.Date.from_string(base_date)

            min_service = leave_type.allocation_min
            min_type = leave_type.min_type

            diff = relativedelta(base_date, join_date)
            total_months = diff.years * 12 + diff.months
            total_days = (base_date - join_date).days

            if min_type == 'day' and total_days < min_service:
                raise ValidationError(_("Minimum day requirement not met"))

            if min_type == 'month' and total_months < min_service:
                raise ValidationError(_("Minimum month requirement not met"))

            if min_type == 'year' and diff.years < min_service:
                raise ValidationError(_("Minimum year requirement not met"))

            configs = leave_type.leave_config_ids.sorted(key=lambda x: x.months_count)

            if not configs:
                alloc.number_of_days = 0
                continue

            entitlement_now = 0
            for cfg in configs:
                if total_months >= cfg.months_count:
                    entitlement_now = cfg.added_value

            alloc.number_of_days = entitlement_now

            alloc.allocation_ids.unlink()

            self._generate_future_sick_allocations(
                alloc=alloc,
                join_date=join_date,
                configs=configs,
                base_month=total_months,
                current_entitlement=entitlement_now
            )

    def _generate_future_sick_allocations(
        self, alloc, join_date, configs, base_month, current_entitlement):

        next_month = alloc.date_from + relativedelta(months=1)
        prev_entitlement = current_entitlement
        max_month = max(configs.mapped('months_count'))

        while True:

            diff = relativedelta(next_month, join_date)
            total_months = diff.years * 12 + diff.months

            if total_months > max_month:
                break

            entitlement = 0
            for cfg in configs:
                if total_months >= cfg.months_count:
                    entitlement = cfg.added_value

            increment = entitlement - prev_entitlement

            if increment > 0:
                self.env['hr.leave.allocation'].with_context(skip_leave_calculation=True).create({
                    'allocation_id': alloc.id,
                    'employee_id': alloc.employee_id.id,
                    'holiday_status_id': alloc.holiday_status_id.id,
                    'date_from': next_month,
                    'date_to': alloc.date_to,
                    'number_of_days': increment,
                })
                prev_entitlement = entitlement

            next_month += relativedelta(months=1)
    
    def calculate_maternity_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'maternity':
                continue

            employee = alloc.employee_id
            join_date = employee.join_date
            base_date = alloc.date_from
            leave_type = alloc.holiday_status_id

            allocation_min = leave_type.allocation_min
            allocation_type = leave_type.allocation_type

            if not employee or not join_date or not base_date:
                alloc.number_of_days = 0
                continue

            join_date = fields.Date.from_string(join_date)
            base_date = fields.Date.from_string(base_date)

            min_required_date = allocation_min and base_date - relativedelta(
                months=allocation_min if allocation_type == 'months' else 0
            )

            if min_required_date and join_date > min_required_date:
                raise ValidationError(_("Employee has not met minimum service requirement"))

            if not employee.is_pregnant:
                raise ValidationError("Employee must be pregnant to be eligible for Maternity Leave.")

            child_is_sg = False

            if employee.country_id and employee.country_id.code == 'SG':
                child_is_sg = True
            else:
                if employee.spouse_country_id and employee.spouse_country_id.code == 'SG':
                    child_is_sg = True

            sg_code = 'yes' if child_is_sg else 'no'
            maternity_config = leave_type.leave_config_ids.sorted(key=lambda x: x.sg_citizen_type == sg_code, reverse=True)[:1]

            if not maternity_config:
                raise ValidationError("Maternity leave configuration for this citizenship not found.")

            alloc.number_of_days = maternity_config.added_value

    def calculate_paternity_leave_allocation(self):
        for alloc in self:
            if alloc.employee_id.sex != 'male' and alloc.holiday_status_id.leave_type == 'paternity':
                raise ValidationError("Employee is not Male and not Eligible for Paternity Leave.")
                
            today = fields.Date.today()
            join_date = alloc.employee_id.join_date
            diff = relativedelta(today, join_date)
            total_months = diff.years * 12 + diff.months
            min_service = alloc.holiday_status_id.allocation_min if alloc.holiday_status_id.allocation_min and alloc.holiday_status_id.allocation_type == 'month' else 3

            if not join_date:
                raise ValidationError("Employee Join Date is Required")

            if total_months < min_service:
                raise ValidationError(f"Employee Have Not Worked For Over {min_service} Month and Not Eligible for Paternity Leave")
            
            paternity_config = alloc.holiday_status_id.leave_config_ids
            is_spouse_pregnant = alloc.employee_id.is_spouse_pregnant
            marriage_date = alloc.employee_id.marriage_date
            if is_spouse_pregnant:
                edd_date = alloc.employee_id.edd_date
                
                if not marriage_date or not edd_date:
                    raise ValidationError("Marriage Date and Estimated Delivery Date are Required")

                if marriage_date > edd_date:
                    raise ValidationError("Not Eligible for Paternity Leave, Marriage is After Expected Delivery Date")
                
                is_spouse_singaporean = alloc.employee_id.spouse_country_id.code == 'SG'
                has_sg_children = bool(alloc.employee_id.children_ids.filtered(lambda x: x.is_singapore_citizen == 'yes'))
                is_child_singaporean = (is_spouse_singaporean and alloc.employee_id.marital == 'married') or has_sg_children
                
                if is_child_singaporean:
                    config = paternity_config.filtered(lambda x: x.sg_citizen_type == 'yes')
                    alloc.number_of_days = config.added_value if config else 0.0
                else:
                    raise ValidationError("Not Eligible for Paternity Leave, Employee and Employee's Spouse isn't Singaporean")
                    
            elif alloc.employee_id.children_ids:
                eligible_for_paternity = False
                
                for child in alloc.employee_id.children_ids:
                    if not child.dob:
                        continue

                    if child.is_singapore_citizen == 'yes' and child.children_type == 'biological':
                        if not marriage_date:
                            raise ValidationError("Marriage date is required")
                        
                        legal_deadline = child.dob + relativedelta(months=12)

                        if marriage_date <= legal_deadline:
                            eligible_for_paternity = True
                            break
                    
                    elif child.is_singapore_citizen == 'yes' and child.children_type == 'adopted':
                        if not child.formal_intent_to_adopt_date or not alloc.holiday_status_id.eligible_from_date:
                            continue

                        fia_date = child.formal_intent_to_adopt_date
                        child_birthdate = child.dob
                        eligible_fia_date = alloc.holiday_status_id.eligible_from_date

                        if fia_date < eligible_fia_date:
                            continue
                        else:
                            age_at_fia = relativedelta(fia_date, child_birthdate)
                            if alloc.holiday_status_id.min_type != 'month' or alloc.holiday_status_id.max_type != 'month':
                                raise ValidationError("Min and Max Type Should be in Month")
                            
                            max_age = alloc.holiday_status_id.max_count
                            if age_at_fia.years * 12  + age_at_fia.months <= max_age:
                                eligible_for_paternity = True
                                break
                
                citizen_type = 'yes' if eligible_for_paternity else 'no'
                config = paternity_config.filtered(lambda x:x.sg_citizen_type == citizen_type)
                
                # if not config or config.added_value <= 0:
                #     raise ValidationError("Not Eligible for Paternity Leave")
                
                alloc.number_of_days = config.added_value

            else:
                raise ValidationError("Employee must have a pregnant spouse or existing children to apply for paternity leave")
    
    def calculate_childcare_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'childcare':
                continue

            if not alloc.employee_id.children_ids:
                raise ValidationError("Not Eligible for Childcare Leave. Employee Have No Children")
            
            today = fields.Date.today()
            join_date = alloc.employee_id.join_date
            diff = relativedelta(today, join_date)
            total_months = diff.years * 12 + diff.months
            min_service = alloc.holiday_status_id.allocation_min if alloc.holiday_status_id.allocation_min and alloc.holiday_status_id.allocation_type == 'month' else 3

            if total_months < min_service:
                raise ValidationError(f"Employee Have Not Worked For Over {min_service} Month and Not Eligible for Child Care Leave")

            childcare_config = alloc.holiday_status_id.leave_config_ids
            if alloc.holiday_status_id.min_type != 'year' or alloc.holiday_status_id.max_type != 'year':
                raise ValidationError(" Age Min and Age Max Type Should be in Years")
            
            children = alloc.employee_id.children_ids.filtered(lambda x: x.dob)
            eligible_max_age = alloc.holiday_status_id.max_count

            youngest_child = max(children, key=lambda x: x.dob)
            youngest_child_age = relativedelta(today, youngest_child.dob).years

            if youngest_child_age > eligible_max_age:
                raise ValidationError(f"Youngest child is above {eligible_max_age}")

            if youngest_child.is_singapore_citizen != 'yes':
                alloc.number_of_days = childcare_config.filtered(lambda x:x.sg_citizen_type == 'no').added_value
            else:
                alloc.number_of_days = childcare_config.filtered(lambda x: x.sg_citizen_type == 'yes').added_value

    def calculate_extended_childcare_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'extended_childcare':
                continue

            if not alloc.employee_id.children_ids:
                raise ValidationError("Not Eligible for Extended Childcare Leave. Employee Have No Children")
            
            today = fields.Date.today()
            join_date = alloc.employee_id.join_date
            diff = relativedelta(today, join_date)
            total_months = diff.years * 12 + diff.months
            min_service = alloc.holiday_status_id.allocation_min if alloc.holiday_status_id.allocation_min and alloc.holiday_status_id.allocation_type == 'month' else 3

            if total_months < min_service:
                raise ValidationError(f"Employee Have Not Worked For Over {min_service} Month and Not Eligible for Extended Child Care Leave")
            
            if alloc.holiday_status_id.min_type != 'year' or alloc.holiday_status_id.max_type != 'year':
                raise ValidationError(" Age Min and Age Max Type Should be in Years")
            
            children = alloc.employee_id.children_ids.filtered(lambda x: x.dob)
            youngest_child = max(children, key=lambda x: x.dob)
            youngest_age = relativedelta(today, youngest_child.dob).years

            eligible_min_age = alloc.holiday_status_id.min_count
            eligible_max_age = alloc.holiday_status_id.max_count

            if youngest_age < eligible_min_age:
                raise ValidationError("Eligible under Child Care Leave (GPCL), Not Extended Child Care Leave")
            
            if youngest_age > eligible_max_age:
                raise ValidationError("Child age above 12 and Not Eligible for Extended Child Care Leave")
            
            ecl_config = alloc.holiday_status_id.leave_config_ids
            
            if youngest_child.is_singapore_citizen != 'yes':
                alloc.number_of_days = ecl_config.filtered(lambda x:x.sg_citizen_type == 'no').added_value
            
            alloc.number_of_days = ecl_config.filtered(lambda x: x.sg_citizen_type == 'yes').added_value

    def calculate_unpaid_infant_care_leave(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'infant_care':
                continue
            
            if not alloc.employee_id.children_ids:
                raise ValidationError("Not Eligible for Unpaid Infant Care Leave. Employee Have No Children")
            
            today = fields.Date.today()
            join_date = alloc.employee_id.join_date
            diff = relativedelta(today, join_date)
            total_months = diff.years * 12 + diff.months
            min_service = alloc.holiday_status_id.allocation_min if alloc.holiday_status_id.allocation_min and alloc.holiday_status_id.allocation_type == 'month' else 3

            if total_months < min_service:
                raise ValidationError(f"Employee Have Not Worked For Over {min_service} Month and Not Eligible for Unpaid Infant Care Leave")
            
            if alloc.holiday_status_id.min_type != 'year' or alloc.holiday_status_id.max_type != 'year':
                raise ValidationError(" Age Min and Age Max Type Should be in Years")


            agreement_from_date = alloc.date_from
            agreement_to_date = alloc.date_to

            if not agreement_from_date or not agreement_to_date:
                raise ValidationError("Validity Period must exist")
            
            eligible_period = agreement_from_date + relativedelta(months=12)
            
            if agreement_to_date > eligible_period:
                raise ValidationError("Validity Period must be 12 months")

            if not agreement_from_date <= today <= agreement_to_date:
                raise ValidationError("Not Eligible for Unpaid Infant Care Leave, Current Date is Outside the Agreed Agreement ")
           
            eligible_for_infant_care = None
            eligible_max_age = alloc.holiday_status_id.max_count
            for child in alloc.employee_id.children_ids:
                child_age = relativedelta(today, child.dob).years
                # if child.is_singapore_citizen == 'yes' and child_age <= eligible_max_age:
                #     eligible_for_infant_care = True
                #     break
                if child_age <= eligible_max_age:
                    eligible_for_infant_care = child
                    break

            if not eligible_for_infant_care:
                raise ValidationError("Not Eligible for Unpaid Infant Care Leave, No child below age limit")
            
            infant_care_config = alloc.holiday_status_id.leave_config_ids

            if eligible_for_infant_care.is_singapore_citizen == 'yes':
                alloc.number_of_days = infant_care_config.filtered(lambda x: x.sg_citizen_type == 'yes').added_value
            else:
                alloc.number_of_days = infant_care_config.filtered(lambda x:x.sg_citizen_type == 'no').added_value

    def calculate_adoption_leave(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'adoption_childcare':
                continue

            if alloc.employee_id.sex != 'female':
                raise ValidationError("Not Eligible for Adoption Leave, Employee isn't Female")
            
            if not alloc.employee_id.children_ids:
                raise ValidationError("Not Elgible for Adoption Leave. Employee Have No Children")

            join_date = alloc.employee_id.join_date
            min_service = alloc.holiday_status_id.allocation_min if alloc.holiday_status_id.allocation_min and alloc.holiday_status_id.allocation_type == 'month' else 3
            
            if alloc.holiday_status_id.min_type != 'month' or alloc.holiday_status_id.max_type != 'month':
                raise ValidationError("Age Min and Age Max Type Should be in Month")
            
            adopted_children = alloc.employee_id.children_ids.filtered(lambda x: x.children_type == 'adopted')
            print(adopted_children, 'adopted childrennnnnnnnnnn')

            if not adopted_children:
                raise ValidationError("Employee's Children is Not Adopted and Not Eligible for Adoption Leave")
 
            eligible_for_adoption_leave = False
            eligible_max_age = alloc.holiday_status_id.max_count
            is_child_singaporean = False
            errors = []
            for child in adopted_children:
                if not child.formal_intent_to_adopt_date:
                    errors.append("Missing FIA Date")
                    continue

                diff = relativedelta(child.formal_intent_to_adopt_date, join_date)
                total_months = diff.years * 12 + diff.months
                
                if total_months < min_service:
                    errors.append(f"Employee Have Not Worked For Over {min_service} Month and Not Eligible for Unpaid Infant Care Leave")
                    continue

                child_age = relativedelta(child.formal_intent_to_adopt_date, child.dob)
                child_age_in_month = child_age.years * 12 + child_age.months

                if child_age_in_month > eligible_max_age:
                    errors.append(f"Child Age is > {eligible_max_age} Months ")
                    continue
                
                child_is_singaporean = False
                if child.adoption_type == 'local':
                    if child.is_singapore_citizen == 'yes':
                        child_is_singaporean = True
                        # errors.append('Child is Not Singaporean')
                    else:
                        continue
                else:
                    employee = alloc.employee_id
                    mom_singaporean = employee.country_id.code == 'SG'
                    dad_singaporean = employee.spouse_country_id.code == 'SG' if employee.marital == 'married' else False
                    parent_is_sg = mom_singaporean or dad_singaporean
                    
                    if not parent_is_sg:
                        errors.append('One of the Parent Must Be Singaporean')
                        continue

                    child_is_singaporean = True
                
                if child.adoption_order_date > child.formal_intent_to_adopt_date + relativedelta(years=1):
                    errors.append("Adoption Order Date must be within 1 year after FIA")
                    continue

                eligible_for_adoption_leave = True
                is_child_singaporean = child_is_singaporean
                break
            
            adoption_leave_config = alloc.holiday_status_id.leave_config_ids
            if is_child_singaporean:
                alloc.number_of_days = adoption_leave_config.filtered(lambda x: x.sg_citizen_type == 'yes').added_value
            else:
                if errors:
                    raise ValidationError("; ".join(set(errors)))
                alloc.number_of_days = adoption_leave_config.filtered(lambda x: x.sg_citizen_type == 'no').added_value
            
            if not eligible_for_adoption_leave:
                raise ValidationError("; ".join(set(errors)))
    
    def calculate_no_pay_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'no_pay':
                continue
            no_pay_config = alloc.holiday_status_id.leave_config_ids[0] if alloc.holiday_status_id.leave_config_ids else False

            if not no_pay_config:
                raise ValidationError("No Pay leave configuration for this allocation not found.")

            alloc.number_of_days = no_pay_config.added_value
    
    def calculate_marriage_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'marriage':
                continue
            no_pay_config = alloc.holiday_status_id.leave_config_ids[0] if alloc.holiday_status_id.leave_config_ids else False

            if not no_pay_config:
                raise ValidationError("No Marriage configuration for this allocation not found.")

            alloc.number_of_days = no_pay_config.added_value
    
    def calculate_compassionate_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'compassionate':
                continue
            no_pay_config = alloc.holiday_status_id.leave_config_ids[0] if alloc.holiday_status_id.leave_config_ids else False

            if not no_pay_config:
                raise ValidationError("No Compassionate leave configuration for this allocation not found.")

            alloc.number_of_days = no_pay_config.added_value
    
    def calculate_national_service_leave_allocation(self):
        for alloc in self:
            if alloc.holiday_status_id.leave_type != 'national_service':
                continue
            no_pay_config = alloc.holiday_status_id.leave_config_ids[0] if alloc.holiday_status_id.leave_config_ids else False

            if not no_pay_config:
                raise ValidationError("No National Leave leave configuration for this allocation not found.")

            alloc.number_of_days = no_pay_config.added_value

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if not self.env.context.get("skip_leave_calculation") :
            if rec.holiday_status_id.leave_type == 'annual':
                rec.with_context(skip_leave_calculation=True).calculate_annual_leave_allocation()

            if rec.holiday_status_id.leave_type in ['sick', 'hospitalisation']:
                rec.with_context(skip_leave_calculation=True).calculate_sick_leave_allocation()

            if rec.holiday_status_id.leave_type == 'maternity':
                rec.with_context(skip_leave_calculation=True).calculate_maternity_leave_allocation()

            if rec.holiday_status_id.leave_type == 'paternity':
                rec.with_context(skip_leave_calculation=True).calculate_paternity_leave_allocation()
            
            if rec.holiday_status_id.leave_type == 'childcare':
                rec.with_context(skip_leave_calculation=True).calculate_childcare_leave_allocation()

            if rec.holiday_status_id.leave_type == 'extended_childcare':
                rec.with_context(skip_leave_calculation=True).calculate_extended_childcare_leave_allocation()

            if rec.holiday_status_id.leave_type == 'adoption_childcare':
                rec.with_context(skip_leave_calculation=True).calculate_adoption_leave()
            
            if rec.holiday_status_id.leave_type == 'infant_care':
                rec.with_context(skip_leave_calculation=True).calculate_unpaid_infant_care_leave()
            
            if rec.holiday_status_id.leave_type == 'no_pay':
                rec.with_context(skip_leave_calculation=True).calculate_no_pay_leave_allocation()
            
            if rec.holiday_status_id.leave_type == 'marriage':
                rec.with_context(skip_leave_calculation=True).calculate_marriage_leave_allocation()
            
            if rec.holiday_status_id.leave_type == 'compassionate':
                rec.with_context(skip_leave_calculation=True).calculate_compassionate_leave_allocation()
            
            if rec.holiday_status_id.leave_type == 'national_service':
                rec.with_context(skip_leave_calculation=True).calculate_national_service_leave_allocation()

        return rec


    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_leave_calculation"):
            if self.holiday_status_id.leave_type == 'annual':
                self.with_context(skip_leave_calculation=True).calculate_annual_leave_allocation()

            if self.holiday_status_id.leave_type in ['sick', 'hospitalisation']:
                self.with_context(skip_leave_calculation=True).calculate_sick_leave_allocation()

            if self.holiday_status_id.leave_type == 'maternity':
                self.with_context(skip_leave_calculation=True).calculate_maternity_leave_allocation()

            if self.holiday_status_id.leave_type == 'paternity':
                self.with_context(skip_leave_calculation=True).calculate_paternity_leave_allocation()

            if self.holiday_status_id.leave_type == 'childcare':
                self.with_context(skip_leave_calculation=True).calculate_childcare_leave_allocation()

            if self.holiday_status_id.leave_type == 'extended_childcare':
                self.with_context(skip_leave_calculation=True).calculate_extended_childcare_leave_allocation()

            if self.holiday_status_id.leave_type == 'adoption_childcare':
                self.with_context(skip_leave_calculation=True).calculate_adoption_leave()
            
            if self.holiday_status_id.leave_type == 'infant_care':
                self.with_context(skip_leave_calculation=True).calculate_unpaid_infant_care_leave()
            
            if self.holiday_status_id.leave_type == 'no_pay':
                self.with_context(skip_leave_calculation=True).calculate_no_pay_leave_allocation()
            
            if self.holiday_status_id.leave_type == 'marriage':
                self.with_context(skip_leave_calculation=True).calculate_marriage_leave_allocation()
            
            if self.holiday_status_id.leave_type == 'compassionate':
                self.with_context(skip_leave_calculation=True).calculate_compassionate_leave_allocation()
            
            if self.holiday_status_id.leave_type == 'national_service':
                self.with_context(skip_leave_calculation=True).calculate_national_service_leave_allocation()

        return res




